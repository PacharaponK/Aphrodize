import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.core.config import settings
from backend.core.db.session import get_session

DBSession = Depends(get_session)
security = HTTPBasic()


def require_api_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    username_valid = secrets.compare_digest(credentials.username, settings.api_username)
    password_valid = secrets.compare_digest(credentials.password, settings.api_password)
    if not (username_valid and password_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
