from fastapi import FastAPI

app = FastAPI(
    title="ConvAgent API",
    version="1.0.0"
)



@app.get("/")
def home():
    return {"status": "API is running 🚀"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

