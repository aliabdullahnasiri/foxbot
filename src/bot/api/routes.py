from fastapi import APIRouter

from bot.api.routers.health import router as health_router


def create_app_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    return router
