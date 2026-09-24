from fastapi import APIRouter, Depends

from backend.api.deps import require_api_credentials
from backend.api.v1.routes import (
    analyses,
    consents,
    forecasts,
    health,
    inference,
    questionnaires,
    training,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
protected = [Depends(require_api_credentials)]
api_router.include_router(
    consents.router, prefix="/consents", tags=["consents"], dependencies=protected
)
api_router.include_router(
    questionnaires.router,
    prefix="/questionnaires",
    tags=["questionnaires"],
    dependencies=protected,
)
api_router.include_router(
    analyses.router, prefix="/analyses", tags=["analyses"], dependencies=protected
)
api_router.include_router(
    forecasts.router,
    prefix="/lifestyle-forecast",
    tags=["lifestyle-forecast"],
    dependencies=protected,
)
api_router.include_router(
    training.router, prefix="/training", tags=["training"], dependencies=protected
)
api_router.include_router(
    inference.router, prefix="/inference", tags=["inference"], dependencies=protected
)
api_router.include_router(users.router, prefix="/users", tags=["users"], dependencies=protected)
