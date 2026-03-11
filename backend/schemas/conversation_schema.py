from pydantic import BaseModel, field_validator

class LoginRequest(BaseModel):
    username: str
    encoded: str

class CreateConversationRequest(BaseModel):
    user_id: str

    @field_validator("user_id")
    @classmethod
    def user_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v

class SendMessageRequest(BaseModel):
    message: str