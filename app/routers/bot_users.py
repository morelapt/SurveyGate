from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models import Device, Service, User, UserIdentity, user_devices, user_services
from app.services.users import register_user, update_user_profile


router = APIRouter(prefix="/bot/users", tags=["bot-users"])


class RegisterIn(BaseModel):
    telegram_id: int = Field(..., ge=1)


class RegisterOut(BaseModel):
    is_new: bool
    user_id: int


@router.post("/register", response_model=RegisterOut)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_db_session)):
    is_new, user_id = await register_user(session=session, telegram_id=payload.telegram_id)
    return RegisterOut(is_new=is_new, user_id=user_id)



class ProfileIn(BaseModel):
    telegram_id: int = Field(..., ge=1)
    city: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    has_children: bool | None = None
    devices: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class ProfileOut(BaseModel):
    ok: bool


@router.patch("/profile", response_model=ProfileOut)
async def update_profile(payload: ProfileIn, session: AsyncSession = Depends(get_db_session)):
    try:
        await update_user_profile(
            session=session,
            telegram_id=payload.telegram_id,
            city=payload.city,
            age=payload.age,
            has_children=payload.has_children,
            device_codes=payload.devices,
            service_codes=payload.services,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "User not registered":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "User not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg.startswith("Unknown"):
            raise HTTPException(status_code=400, detail=msg)
        raise

    return ProfileOut(ok=True)

