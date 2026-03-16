from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes.router import router
from backend.api.routes.conversations import websocket_chat

app = FastAPI()

# CORS: allow frontend (e.g. React on :3000) to call this API; fixes OPTIONS 405
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}

app.add_api_websocket_route("/api/v1/ws/{conversation_id}", websocket_chat)