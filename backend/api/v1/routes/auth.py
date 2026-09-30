import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from backend.api.deps import require_user_token
from backend.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    SkinProfileResponse,
)
from backend.api.schemas.consent import WellnessProfileUpsert
from backend.core.db.models import Account, AccountRole, Consent, Questionnaire, User, UserProfile
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
    profile = await session.get(UserProfile, user_id)
    questionnaire = await session.scalar(
        select(Questionnaire)
        .where(Questionnaire.user_id == user_id)
        .order_by(Questionnaire.created_at.desc(), Questionnaire.id.desc())
        .limit(1)
    )
    age_years = questionnaire.answers.get("age_years") if isinstance(questionnaire, Questionnaire) else None
    return SkinProfileResponse(
        user_id=user_id,
        display_name=account.display_name,
        email=account.email,
        profile=(
            {
                "sex": profile.sex,
                "age_group": profile.age_group,
                "skin_type": profile.skin_type,
                "wellness_goal": profile.wellness_goal,
                "sunscreen_frequency": profile.sunscreen_frequency,
                "menstrual_tracking": profile.menstrual_tracking,
                **({"age_years": age_years} if isinstance(age_years, (int, float)) else {}),
            }
            if profile else None
        ),
        answers=questionnaire.answers if isinstance(questionnaire, Questionnaire) else None,
    )


@router.put("/daily-health-consent", status_code=status.HTTP_200_OK)
async def grant_daily_health_consent(
    user_id: uuid.UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if await session.scalar(select(Account.id).where(Account.user_id == user_id)) is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    existing = await session.scalar(
        select(Consent.id).where(
            Consent.user_id == user_id,
            Consent.version == "daily-health-v1",
            Consent.revoked_at.is_(None),
        ).limit(1)
    )
    if existing is None:
        session.add(Consent(user_id=user_id, version="daily-health-v1"))
        await session.commit()
    return {"status": "granted"}


@router.put("/profile", status_code=status.HTTP_200_OK)
async def save_wellness_profile(
    payload: WellnessProfileUpsert,
    user_id: uuid.UUID = Depends(require_user_token),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    consent = await session.scalar(
        select(Consent.id).where(
            Consent.user_id == user_id,
            Consent.version == "signup-v1",
            Consent.revoked_at.is_(None),
        ).limit(1)
    )
    if consent is None:
        raise HTTPException(status_code=403, detail="Active consent is required")
    if payload.age_group == "under_13":
        guardian_consent = await session.scalar(
            select(Consent.id).where(
                Consent.user_id == user_id,
                Consent.version == "guardian-health-v1",
                Consent.revoked_at.is_(None),
            ).limit(1)
        )
        if guardian_consent is None:
            session.add(Consent(user_id=user_id, version="guardian-health-v1"))
    values = payload.profile_values()
    statement = insert(UserProfile).values(user_id=user_id, **values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[UserProfile.user_id],
            set_={
                **{key: getattr(statement.excluded, key) for key in values},
                "updated_at": func.now(),
            },
        )
    )
    await session.commit()
    return {"status": "saved"}


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
        raise HTTPException(
            status_code=422, detail="Consent is required before creating an account"
        )
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
