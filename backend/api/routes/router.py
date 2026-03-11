from fastapi import APIRouter
from backend.api.routes.user_login import router as login_router
from backend.api.routes.conversations import router as conversations_router

router = APIRouter()

router.include_router(login_router)
router.include_router(conversations_router)