from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.schemas.operator import (
    CreatedInviteOut,
    SegmentCreateIn,
    SegmentCreateOut,
    SendInvitationsIn,
    SendInvitationsOut,
    SurveyCreateIn,
    SurveyCreateOut,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db_session
from app.services.operator import create_survey, create_segment
from app.services.segments_validate import validate_segment_tree
from app.services.segments_compiler import compile_segment_query
from app.models import Segment, User
from app.services.send_invitations import send_invitations


def require_operator_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not x_api_key or x_api_key != settings.OPERATOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )

router = APIRouter(
    prefix="/operator",
    tags=["operator"],
    dependencies=[Depends(require_operator_key)],
)


@router.get("/ping")
async def ping():
    return {"ok": True}

@router.post("/surveys", response_model=SurveyCreateOut)
async def create_survey_endpoint(payload: SurveyCreateIn, session: AsyncSession = Depends(get_db_session)):
    survey_id = await create_survey(session=session, title=payload.title, status=payload.status)
    return SurveyCreateOut(survey_id=survey_id)

@router.post("/segments", response_model=SegmentCreateOut)
async def create_segment_endpoint(payload: SegmentCreateIn, session: AsyncSession = Depends(get_db_session)):
    try:
        validate_segment_tree(payload.filters)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    segment_id = await create_segment(session=session, name=payload.name, filters=payload.filters)
    return SegmentCreateOut(segment_id=segment_id)

@router.get("/segments/{segment_id}/preview")
async def preview_segment(
    segment_id: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
):
    segment = await session.get(Segment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    stmt = compile_segment_query(segment.filters).with_only_columns(User.id).limit(limit)
    res = await session.execute(stmt)
    user_ids = [row[0] for row in res.all()]
    return {"segment_id": segment_id, "user_ids": user_ids}


@router.post("/surveys/{survey_id}/send_invitations", response_model=SendInvitationsOut)
async def send_invitations_endpoint(
    survey_id: int,
    payload: SendInvitationsIn,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        result = await send_invitations(
            session=session,
            survey_id=survey_id,
            segment_id=payload.segment_id,
            message_template=payload.message_template,
            ttl_days=payload.ttl_days,
            limit=payload.limit,
        )
    except ValueError as e:
        msg = str(e)
        if msg.endswith("not found"):
            raise HTTPException(status_code=404, detail=msg)
        if msg in {"Survey is closed"}:
            raise HTTPException(status_code=400, detail=msg)
        raise

    return SendInvitationsOut(**result)

