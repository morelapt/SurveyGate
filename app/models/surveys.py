import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    starts_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )

    __table_args__ = (
        CheckConstraint("status in ('draft','active','closed')", name="ck_surveys_status"),
        Index("ix_surveys_status", "status"),
    )
