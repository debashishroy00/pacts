from fastapi import FastAPI
app = FastAPI(title="PACTS Backend API")

@app.get("/health")
def health():
    return {"status": "ok"}
