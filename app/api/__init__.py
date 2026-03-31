from fastapi import APIRouter

from app.api.campaigns import router as campaigns_router
from app.api.modules import router as modules_router
from app.api.query import router as query_router
from app.api.state import state_router, session_router

api_router = APIRouter()

api_router.include_router(campaigns_router)
api_router.include_router(modules_router)
api_router.include_router(query_router)
api_router.include_router(state_router)
api_router.include_router(session_router)
