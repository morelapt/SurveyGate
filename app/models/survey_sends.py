import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SurveySend(Base):
    __tablename__ = "survey_sends"

    id: Mapped[int] = mapped_column(primary_key=True)

    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("segments.id", ondelete="RESTRICT"), nullable=False
    )

    message_template: Mapped[str] = mapped_column(String, nullable=False)
    ttl_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )

    __table_args__ = (
        Index("ix_survey_sends_survey_id", "survey_id"),
        Index("ix_survey_sends_segment_id", "segment_id"),
    )
