from fastapi import APIRouter

from itk_academy.api.v1 import health, sync

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(sync.router, tags=["sync"])
