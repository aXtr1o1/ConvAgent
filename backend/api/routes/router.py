from fastapi import APIRouter
from backend.api.routes.user_login import router as login_router
from backend.api.routes.conversations import router as conversations_router
from backend.api.routes.ingest        import router as ingest_router 
from backend.api.routes.diagnose      import router as diagnose_router 

router = APIRouter()

router.include_router(login_router)
router.include_router(conversations_router)
router.include_router(ingest_router)
router.include_router(diagnose_router)        