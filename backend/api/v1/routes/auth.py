import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_user_token
from backend.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    SkinProfileResponse,
)
from backend.core.db.models import Account, AccountRole, Consent, Questionnaire, User
from backend.core.db.session import get_session
from backend.services.passwords import hash_password, verify_password
from backend.services.tokens import create_access_token

router = APIRouter()


@router.get("/profile", response_model=SkinProfileResponse)
async def skin_profile(
    user_id: uuid.UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> SkinProfileResponse:
    account = await session.scalar(select(Account).where(Account.user_id == user_id))
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    questionnaire = await session.scalar(
        select(Questionnaire)
        .where(Questionnaire.user_id == user_id)
        .order_by(Questionnaire.created_at.desc())
        .limit(1)
    )
    return SkinProfileResponse(
        display_name=account.display_name,
        email=account.email,
        answers=questionnaire.answers if questionnaire else None,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> LoginResponse:
    account = await session.scalar(select(Account).where(Account.email == payload.email))
    if account is None or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return LoginResponse(
        user_id=account.user_id,
        display_name=account.display_name,
        access_token=create_access_token(account.user_id),
    )


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest, session: AsyncSession = Depends(get_session)
) -> SignupResponse:
    if not payload.consent_accepted:
        raise HTTPException(status_code=422, detail="Consent is required before creating an account")
    existing = await session.scalar(select(Account.id).where(Account.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    user = User(id=uuid.uuid4())
    account = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        display_name=payload.display_name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    consent = Consent(user_id=user.id, version="signup-v1")
    member_role = AccountRole(account_id=account.id, role="member")
    # Flush the parent first so PostgreSQL can satisfy the account/consent foreign keys.
    session.add(user)
    await session.flush()
    session.add_all([account, member_role, consent])
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if "accounts_email" in str(error.orig):
            raise HTTPException(
                status_code=409, detail="An account already exists for this email"
            ) from None
        raise HTTPException(status_code=500, detail="Unable to create account") from error

    return SignupResponse(
        user_id=user.id,
        display_name=account.display_name,
        email=account.email,
        access_token=create_access_token(user.id),
    )
