from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    telegram_id: int = Field(..., ge=1)


class RegisterOut(BaseModel):
    is_new: bool
    user_id: int


class ProfileIn(BaseModel):
    telegram_id: int = Field(..., ge=1)
    city: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    has_children: bool | None = None
    devices: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class ProfileOut(BaseModel):
    ok: bool
