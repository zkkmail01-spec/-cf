from fastapi import APIRouter

from app.api.v1.endpoints import dishes, families, session


api_router = APIRouter()
api_router.include_router(session.router)
api_router.include_router(families.router)
api_router.include_router(dishes.router)
