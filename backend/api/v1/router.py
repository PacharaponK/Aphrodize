from fastapi import APIRouter, Depends

from backend.api.deps import require_admin_credentials, require_api_credentials
from backend.api.v1.routes import (
    acne,
    analyses,
    auth,
    consents,
    daily_health,
    health,
    inference,
    monitoring,
    products,
    questionnaires,
    training,
    users,
    uv,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(acne.router, prefix="/acne", tags=["acne"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
protected = [Depends(require_api_credentials)]
api_router.include_router(
    consents.router, prefix="/consents", tags=["consents"], dependencies=protected
)
api_router.include_router(consents.user_router, prefix="/consents", tags=["consents"])
api_router.include_router(
    questionnaires.router,
    prefix="/questionnaires",
    tags=["questionnaires"],
)
api_router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
api_router.include_router(
    daily_health.router,
    prefix="/daily-health",
    tags=["daily-health"],
    dependencies=protected,
)
api_router.include_router(daily_health.user_router, prefix="/daily-health", tags=["daily-health"])
api_router.include_router(
    daily_health.review_router, prefix="/daily-health", tags=["model review"]
)
api_router.include_router(
    training.router, prefix="/training", tags=["training"], dependencies=protected
)
api_router.include_router(
    inference.router, prefix="/inference", tags=["inference"], dependencies=protected
)
api_router.include_router(
    monitoring.router, prefix="/monitoring", tags=["monitoring"], dependencies=protected
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(uv.router, prefix="/uv", tags=["uv"], dependencies=protected)
api_router.include_router(
    products.router,
    prefix="/admin/products",
    tags=["admin products"],
    dependencies=[Depends(require_admin_credentials)],
)
