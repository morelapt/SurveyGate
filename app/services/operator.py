from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Segment, Survey


async def create_survey(session: AsyncSession, title: str, status: str = "draft") -> int:
    stmt = insert(Survey).values(title=title, status=status).returning(Survey.id)
    res = await session.execute(stmt)
    await session.commit()
    return res.scalar_one()


async def create_segment(session: AsyncSession, name: str, filters: dict) -> int:
    stmt = insert(Segment).values(name=name, filters=filters).returning(Segment.id)
    res = await session.execute(stmt)
    await session.commit()
    return res.scalar_one()
