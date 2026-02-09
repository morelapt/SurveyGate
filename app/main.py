from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db_session
from app.routers.bot_users import router as bot_users_router


@asynccontextmanager
async def lifespan(app_: FastAPI):
    # startup
    print("ENV:", settings.ENV)
    print("DATABASE_URL:", settings.DATABASE_URL)

    yield

    # shutdown
    print("Shutting down...")


app = FastAPI(title="SurveyGate API", lifespan=lifespan)
app.include_router(bot_users_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
