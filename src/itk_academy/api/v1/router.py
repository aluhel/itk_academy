from fastapi import APIRouter

from itk_academy.api.v1 import events, health, sync, tickets

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(sync.router, tags=["sync"])
api_router.include_router(tickets.router, tags=["tickets"])
