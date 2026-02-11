from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db_session
from app.services.operator import create_survey, create_segment
from app.services.segments_validate import validate_segment_tree


class SurveyCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    status: str = "draft"


class SurveyCreateOut(BaseModel):
    survey_id: int


class SegmentCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    filters: dict


class SegmentCreateOut(BaseModel):
    segment_id: int


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
