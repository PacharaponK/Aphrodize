import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from backend.core.config import settings
from backend.core.db.session import get_session
from backend.services.tokens import read_access_token

DBSession = Depends(get_session)
security = HTTPBasic()
bearer_security = HTTPBearer(auto_error=False)


def require_api_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    username_valid = secrets.compare_digest(credentials.username, settings.api_username)
    password_valid = secrets.compare_digest(credentials.password, settings.api_password)
    if not (username_valid and password_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def require_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    if not settings.admin_username or len(settings.admin_password) < 8:
        raise HTTPException(status_code=503, detail="Admin access is not configured")
    if not (
        secrets.compare_digest(credentials.username, settings.admin_username)
        and secrets.compare_digest(credentials.password, settings.admin_password)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def require_user_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_security),
) -> UUID:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return read_access_token(credentials.credentials)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def require_matching_user(
    user_id: UUID, caller_id: UUID = Depends(require_user_token)
) -> UUID:
    if user_id != caller_id:
        raise HTTPException(status_code=403, detail="User access denied")
    return caller_id
