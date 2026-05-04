import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.routers.bot_users import router as bot_users_router
from app.routers.operator import router as operator_router
from app.routers.public import router as public_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app_: FastAPI):
    logger.info("SurveyGate application started")
    yield
    logger.info("SurveyGate application stopped")


app = FastAPI(title="SurveyGate API", lifespan=lifespan)

app.include_router(bot_users_router)
app.include_router(operator_router)
app.include_router(public_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
