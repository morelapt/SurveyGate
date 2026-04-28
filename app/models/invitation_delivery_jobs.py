import datetime as dt
from enum import Enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvitationDeliveryStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"


class InvitationDeliveryJob(Base):
    __tablename__ = "invitation_delivery_jobs"

    __table_args__ = (
        UniqueConstraint("invitation_id", name="uq_invitation_delivery_jobs_invitation_id"),
        Index("ix_invitation_delivery_jobs_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invitation_id: Mapped[int] = mapped_column(
        ForeignKey("invitations.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[InvitationDeliveryStatus] = mapped_column(
        SQLEnum(
            InvitationDeliveryStatus,
            name="invitation_delivery_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=InvitationDeliveryStatus.PENDING,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC),
        nullable=False,
    )
    queued_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
