from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models import Device, Service, User, UserIdentity, user_devices, user_services

router = APIRouter(prefix="/bot/users", tags=["bot-users"])


class RegisterIn(BaseModel):
    telegram_id: int = Field(..., ge=1)


class RegisterOut(BaseModel):
    is_new: bool
    user_id: int


@router.post("/register", response_model=RegisterOut)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_db_session)):
    # 1) если identity существует — вернуть is_new=false
    stmt = select(UserIdentity.user_id).where(UserIdentity.telegram_id == payload.telegram_id)
    existing_user_id = await session.scalar(stmt)
    if existing_user_id is not None:
        return RegisterOut(is_new=False, user_id=existing_user_id)

    # 2) иначе создать user + identity (идемпотентно: выдержать гонку)
    user = User()
    session.add(user)
    await session.flush()  # получить user.id

    session.add(UserIdentity(user_id=user.id, telegram_id=payload.telegram_id))

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # если параллельно кто-то создал identity — просто прочитать и вернуть
        existing_user_id = await session.scalar(stmt)
        if existing_user_id is None:
            raise
        return RegisterOut(is_new=False, user_id=existing_user_id)

    return RegisterOut(is_new=True, user_id=user.id)


class ProfileIn(BaseModel):
    telegram_id: int = Field(..., ge=1)
    city: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    has_children: bool | None = None
    devices: list[str] = []
    services: list[str] = []


class ProfileOut(BaseModel):
    ok: bool


@router.patch("/profile", response_model=ProfileOut)
async def update_profile(payload: ProfileIn, session: AsyncSession = Depends(get_db_session)):
    user_id = await session.scalar(
        select(UserIdentity.user_id).where(UserIdentity.telegram_id == payload.telegram_id)
    )
    if user_id is None:
        raise HTTPException(status_code=404, detail="User not registered")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # обновить поля профиля
    user.city = payload.city
    user.age = payload.age
    user.has_children = payload.has_children

    # codes -> ids (справочники должны быть заполнены)
    if payload.devices:
        device_ids = (
            await session.scalars(select(Device.id).where(Device.code.in_(payload.devices)))
        ).all()
        if len(device_ids) != len(set(payload.devices)):
            raise HTTPException(status_code=400, detail="Unknown device code in devices[]")
    else:
        device_ids = []

    if payload.services:
        service_ids = (
            await session.scalars(select(Service.id).where(Service.code.in_(payload.services)))
        ).all()
        if len(service_ids) != len(set(payload.services)):
            raise HTTPException(status_code=400, detail="Unknown service code in services[]")
    else:
        service_ids = []

    try:
        # “перезаписать списки”: удалить старые связи, вставить новые
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

    return ProfileOut(ok=True)
