from fastapi import FastAPI

from app.routers import auth

app = FastAPI(title="Task Flow", version="1.0.0")

app.include_router(auth.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
