from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, Service, User, UserIdentity, user_devices, user_services


async def register_user(session: AsyncSession, telegram_id: int) -> tuple[bool, int]:
    """
    Returns: (is_new, user_id)
    """
    stmt = select(UserIdentity.user_id).where(UserIdentity.telegram_id == telegram_id)

    existing_user_id = await session.scalar(stmt)
    if existing_user_id is not None:
        return False, existing_user_id

    user = User()
    session.add(user)
    await session.flush()  # get user.id

    session.add(UserIdentity(user_id=user.id, telegram_id=telegram_id))

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_user_id = await session.scalar(stmt)
        if existing_user_id is None:
            raise
        return False, existing_user_id

    return True, user.id


async def update_user_profile(
    session: AsyncSession,
    telegram_id: int,
    city: str | None,
    age: int | None,
    has_children: bool | None,
    device_codes: list[str],
    service_codes: list[str],
) -> None:
    user_id = await session.scalar(
        select(UserIdentity.user_id).where(UserIdentity.telegram_id == telegram_id)
    )
    if user_id is None:
        raise ValueError("User not registered")

    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    user.city = city
    user.age = age
    user.has_children = has_children

    # codes -> ids
    if device_codes:
        device_ids = (await session.scalars(select(Device.id).where(Device.code.in_(device_codes)))).all()
        if len(device_ids) != len(set(device_codes)):
            raise ValueError("Unknown device code in devices[]")
    else:
        device_ids = []

    if service_codes:
        service_ids = (await session.scalars(select(Service.id).where(Service.code.in_(service_codes)))).all()
        if len(service_ids) != len(set(service_codes)):
            raise ValueError("Unknown service code in services[]")
    else:
        service_ids = []

    try:
        await session.execute(delete(user_devices).where(user_devices.c.user_id == user_id))
        await session.execute(delete(user_services).where(user_services.c.user_id == user_id))

        if device_ids:
            await session.execute(
                insert(user_devices),
                [{"user_id": user_id, "device_id": did} for did in device_ids],
            )
        if service_ids:
            await session.execute(
                insert(user_services),
                [{"user_id": user_id, "service_id": sid} for sid in service_ids],
            )

        await session.commit()

    except IntegrityError:
        await session.rollback()
        raise
