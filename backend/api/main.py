from fastapi import FastAPI
from .metrics import router as metrics_router

app = FastAPI(title="PACTS Backend API", version="3.0")

@app.get("/health")
def health():
    return {"status": "ok"}

# Mount metrics router (Day 12 Part B)
app.include_router(metrics_router)
