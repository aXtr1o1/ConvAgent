from fastapi import APIRouter
from backend.core.auth_func import user_authFunc
from backend.schemas.conversation_schema import LoginRequest

router = APIRouter()

@router.post("/auth")
def userlog(body: LoginRequest):
    db_user = user_authFunc(body.username)

    if db_user and body.encoded == db_user["bs64"]:
        return {
            "status": "success",
            "user_id": db_user["user_id"],
            "username": body.username
        }

    return {"status": "failed", "detail": "Invalid username or credentials."}