from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.bot_users import (
    ProfileIn,
    ProfileOut,
    RegisterIn,
    RegisterOut,
)
from app.services.users import register_user, update_user_profile

router = APIRouter(prefix="/bot/users", tags=["bot-users"])


@router.post("/register", response_model=RegisterOut)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_db_session)):
    is_new, user_id = await register_user(session=session, telegram_id=payload.telegram_id)
    return RegisterOut(is_new=is_new, user_id=user_id)


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
            raise HTTPException(status_code=404, detail=msg) from e
        if msg == "User not found":
            raise HTTPException(status_code=404, detail=msg) from e
        if msg.startswith("Unknown"):
            raise HTTPException(status_code=400, detail=msg) from e
        raise

    return ProfileOut(ok=True)

