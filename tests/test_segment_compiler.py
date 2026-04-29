import pytest

from app.models import User
from app.services.segments_compiler import compile_segment_query


@pytest.mark.asyncio
async def test_segment_city_eq_filters_users(session):
    # arrange
    u1 = User(city="Moscow", age=20)
    u2 = User(city="Berlin", age=30)

    session.add_all([u1, u2])
    await session.commit()

    filters = {
        "op": "AND",
        "rules": [
            {"field": "city", "op": "EQ", "value": "Moscow"},
        ],
    }

    # act
    stmt = compile_segment_query(filters)
    users = (await session.execute(stmt)).scalars().all()

    # assert
    assert len(users) == 1
    assert users[0].city == "Moscow"
