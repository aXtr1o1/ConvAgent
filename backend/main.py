from fastapi import FastAPI
from backend.api.routes.router import router
from backend.api.routes.conversations import websocket_chat

app = FastAPI()

app.include_router(router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}

app.add_api_websocket_route("/api/v1/ws/{conversation_id}", websocket_chat)