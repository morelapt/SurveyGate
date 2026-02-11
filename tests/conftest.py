import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.settings import settings
from app.models import Segment, Survey, User, UserIdentity


@pytest_asyncio.fixture
async def engine():
    # ВАЖНО: NullPool => нет кэша соединений между тестами/лупами
    eng = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
async def clean_db(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            TRUNCATE TABLE
                invitations,
                survey_sends,
                segments,
                surveys,
                user_identities,
                user_devices,
                user_services,
                users
            RESTART IDENTITY CASCADE;
            """
        )
    )
    await session.commit()


@pytest_asyncio.fixture
def make_user_with_identity(session):
    async def _make(city: str, age: int, has_children: bool):
        user = User(city=city, age=age, has_children=has_children)
        session.add(user)
        await session.flush()  # получаем user.id

        ident = UserIdentity(user_id=user.id, telegram_id=999000 + user.id)
        session.add(ident)

        await session.commit()
        return user

    return _make


@pytest_asyncio.fixture
def make_survey(session):
    async def _make(title: str, status: str = "draft"):
        survey = Survey(title=title, status=status)
        session.add(survey)
        await session.flush()
        await session.commit()
        return survey

    return _make


@pytest_asyncio.fixture
def make_segment_city_eq(session):
    async def _make(name: str, city: str):
        seg = Segment(
            name=name,
            filters={
                "op": "AND",
                "rules": [{"field": "city", "op": "EQ", "value": city}],
            },
        )
        session.add(seg)
        await session.flush()
        await session.commit()
        return seg

    return _make
