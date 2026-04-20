from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.public_responses import (
    get_public_invitation_status,
    submit_public_response,
)

router = APIRouter(tags=["public"])


class PublicResponseIn(BaseModel):
    answers: dict

    @field_validator("answers")
    @classmethod
    def validate_answers_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("answers must not be empty")
        return v


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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if msg in {
            "Invitation revoked",
            "Invitation already used",
            "Invitation expired",
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if msg in {
            "Invitation revoked",
            "Invitation already used",
            "Invitation expired",
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise

    return {
        "ok": True,
        "response_id": response_id,
    }