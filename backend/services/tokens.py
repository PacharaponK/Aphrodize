from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from backend.core.config import settings

ALGORITHM = "HS256"
INSECURE_DEFAULT_SECRET = "change-this-jwt-secret-in-production"


def signing_secret() -> str:
    if settings.app_env.lower() == "production" and settings.jwt_secret_key == INSECURE_DEFAULT_SECRET:
        raise RuntimeError("JWT_SECRET_KEY must be configured in production")
    return settings.jwt_secret_key


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, signing_secret(), algorithm=ALGORITHM)


def read_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(token, signing_secret(), algorithms=[ALGORITHM])
        return UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, ValueError) as error:
        raise ValueError("Invalid or expired access token") from error
