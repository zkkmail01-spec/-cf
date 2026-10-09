from fastapi import APIRouter

from app.api.v1.endpoints import families, session


api_router = APIRouter()
api_router.include_router(session.router)
api_router.include_router(families.router)
