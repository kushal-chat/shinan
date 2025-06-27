from fastapi import APIRouter
from .health import router as health_router
from .client import router as client_router

router = APIRouter()

router.include_router(health_router)
router.include_router(client_router)
