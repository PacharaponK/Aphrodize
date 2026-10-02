from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.schemas.auth import SignupRequest
from backend.api.v1.routes.auth import signup
from backend.core.db.models import Account, AccountRole, Consent, User


class FakeSession:
    def __init__(self, existing_account: bool = False) -> None:
        self.existing_account = existing_account
        self.added: list[object] = []
        self.committed = False

    async def scalar(self, _query: object) -> object | None:
        return "existing" if self.existing_account else None

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        pass

    def add_all(self, values: list[object]) -> None:
        self.added.extend(values)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


def test_signup_request_normalizes_identity_fields() -> None:
    payload = SignupRequest(
        display_name="  Nara  ",
        email="  NARA@EXAMPLE.COM ",
        password="password123",
        consent_accepted=True,
    )
    assert payload.display_name == "Nara"
    assert payload.email == "nara@example.com"


def test_signup_request_rejects_blank_display_name() -> None:
    with pytest.raises(ValidationError):
        SignupRequest(
            display_name="   ",
            email="nara@example.com",
            password="password123",
            consent_accepted=True,
        )


@pytest.mark.asyncio
async def test_signup_creates_account_user_and_consent() -> None:
    session = FakeSession()
    response = await signup(
        SignupRequest(
            display_name="Nara",
            email="nara@example.com",
            password="password123",
            consent_accepted=True,
        ),
        session,
    )

    assert session.committed is True
    assert len(session.added) == 4
    user, account, member_role, consent = session.added
    assert isinstance(user, User)
    assert isinstance(account, Account)
    assert isinstance(member_role, AccountRole)
    assert isinstance(consent, Consent)
    assert account.user_id == user.id
    assert member_role.account_id == account.id
    assert member_role.role == "member"
    assert consent.user_id == user.id
    assert response.user_id == user.id
    assert UUID(str(response.user_id)) == user.id
    assert response.access_token


@pytest.mark.asyncio
async def test_signup_requires_consent_and_unique_email() -> None:
    without_consent = SignupRequest(
        display_name="Nara",
        email="nara@example.com",
        password="password123",
        consent_accepted=False,
    )
    with pytest.raises(HTTPException, match="Consent is required") as consent_error:
        await signup(without_consent, FakeSession())
    assert consent_error.value.status_code == 422

    with pytest.raises(HTTPException, match="already exists") as duplicate_error:
        await signup(
            without_consent.model_copy(update={"consent_accepted": True}), FakeSession(True)
        )
    assert duplicate_error.value.status_code == 409
