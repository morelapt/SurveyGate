import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)

    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    send_id: Mapped[int | None] = mapped_column(
        ForeignKey("survey_sends.id", ondelete="SET NULL"), nullable=True
    )

    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    resend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        # обычные индексы
        Index("ix_invitations_survey_id_user_id", "survey_id", "user_id"),
        Index("ix_invitations_expires_at", "expires_at"),
        # уникальность токена (чтобы не совпал хэш)
        Index("uq_invitations_token_hash", "token_hash", unique=True),
        # "один активный инвайт" — partial unique index (Postgres)
        Index(
            "uq_invitations_active_survey_user",
            "survey_id",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL AND used_at IS NULL"),
        ),
    )
