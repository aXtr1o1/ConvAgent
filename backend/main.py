from fastapi import FastAPI
from backend.api.routes.router import router

app = FastAPI()

app.include_router(router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}