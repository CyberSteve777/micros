from fastapi import FastAPI
from contextlib import asynccontextmanager
from .endpoints.notification_router import notification_router
from .database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database
    init_db()
    yield
    # Shutdown: Clean up resources if needed (none currently)

app = FastAPI(
    title="Notifications Service",
    description="Микросервис для управления уведомлениями",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "notifications"}

app.include_router(notification_router, prefix='/api')
