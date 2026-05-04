from pydantic import BaseModel, Field


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


class SendInvitationsIn(BaseModel):
    segment_id: int
    message_template: str = Field(min_length=1)
    ttl_days: int = Field(default=14, ge=1, le=365)
    limit: int = Field(default=200, ge=1, le=5000)


class CreatedInviteOut(BaseModel):
    user_id: int
    invitation_id: int
    invite_link: str


class SendInvitationsOut(BaseModel):
    send_id: int
    targeted: int
    created: int
    resent: int
    skipped: int
    created_invites: list[CreatedInviteOut] = []
