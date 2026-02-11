from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.settings import settings

router = APIRouter(prefix="/operator", tags=["operator"])


def require_operator_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not x_api_key or x_api_key != settings.OPERATOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


@router.get("/ping", dependencies=[Depends(require_operator_key)])
async def ping():
    return {"ok": True}
