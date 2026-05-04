from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.public import PublicResponseIn
from app.services.public_responses import (
    get_public_invitation_status,
    submit_public_response,
)

router = APIRouter(tags=["public"])


@router.get("/s/{survey_id}/{token}")
async def open_public_invite(
    survey_id: int,
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        return await get_public_invitation_status(
            session=session,
            survey_id=survey_id,
            token=token,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Invitation not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        if msg in {
            "Invitation revoked",
            "Invitation already used",
            "Invitation expired",
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg) from e
        raise


@router.post("/s/{survey_id}/{token}")
async def submit_public_response_endpoint(
    survey_id: int,
    token: str,
    payload: PublicResponseIn,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        response_id = await submit_public_response(
            session=session,
            survey_id=survey_id,
            token=token,
            answers=payload.answers,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Invitation not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        if msg in {
            "Invitation revoked",
            "Invitation already used",
            "Invitation expired",
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg) from e
        raise

    return {
        "ok": True,
        "response_id": response_id,
    }
