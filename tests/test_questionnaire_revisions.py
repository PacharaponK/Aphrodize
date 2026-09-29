from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.schemas.consent import SafetyScreeningUpdate
from backend.api.v1.routes.questionnaires import update_safety_screening


class FakeSession:
    def __init__(self, latest):
        self.latest = latest
        self.added = []
        self.committed = False

    async def scalar(self, _query):
        return self.latest

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_safety_revision_merges_only_safety_answers_after_matching_base_revision():
    user_id = uuid4()
    revision_id = uuid4()
    session = FakeSession(SimpleNamespace(id=revision_id, answers={
        "skin_type": "dry", "sunscreen_frequency": "sometimes",
        "skin_sensitivity": "unsure", "known_product_allergy": "unsure",
        "severe_irritation": "unsure",
    }))
    payload = SafetyScreeningUpdate(
        base_revision_id=revision_id,
        skin_sensitivity="low", known_product_allergy="no", severe_irritation="no",
    )

    result = await update_safety_screening(payload, user_id=user_id, session=session)

    assert result["status"] == "updated"
    assert session.committed is True
    assert session.added[0].answers == {
        "skin_type": "dry", "sunscreen_frequency": "sometimes",
        "skin_sensitivity": "low", "known_product_allergy": "no", "severe_irritation": "no",
    }
    assert "base_revision_id" not in session.added[0].answers


@pytest.mark.asyncio
async def test_safety_revision_rejects_stale_base_instead_of_overwriting_newer_answers():
    session = FakeSession(SimpleNamespace(id=uuid4(), answers={"skin_type": "dry"}))
    payload = SafetyScreeningUpdate(
        base_revision_id=uuid4(),
        skin_sensitivity="low", known_product_allergy="no", severe_irritation="no",
    )

    with pytest.raises(HTTPException) as error:
        await update_safety_screening(payload, user_id=uuid4(), session=session)

    assert error.value.status_code == 409
    assert session.added == []
