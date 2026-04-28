import datetime as dt

from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invitation, InvitationDeliveryJob, InvitationDeliveryStatus
from app.services.delivery import send_message_stub


async def create_invitation_delivery_job(
    session: AsyncSession,
    invitation_id: int,
    telegram_id: int,
    message_text: str,
    created_at: dt.datetime,
) -> int:
    job_stmt = (
        insert(InvitationDeliveryJob)
        .values(
            invitation_id=invitation_id,
            telegram_id=telegram_id,
            message_text=message_text,
            status=InvitationDeliveryStatus.PENDING,
            attempts=0,
            created_at=created_at,
        )
        .returning(InvitationDeliveryJob.id)
    )
    result = await session.execute(job_stmt)
    return result.scalar_one()


async def process_invitation_delivery_job(
    session: AsyncSession,
    job_id: int,
) -> bool:
    job = await session.get(InvitationDeliveryJob, job_id)
    if job is None:
        raise ValueError("Delivery job not found")

    if job.status == InvitationDeliveryStatus.SENT:
        return False

    now = dt.datetime.now(dt.UTC)

    invitation = await session.get(Invitation, job.invitation_id)
    if invitation is None:
        await session.execute(
            update(InvitationDeliveryJob)
            .where(InvitationDeliveryJob.id == job_id)
            .values(
                status=InvitationDeliveryStatus.FAILED,
                last_error="Invitation not found",
            )
        )
        await session.commit()
        return False

    if (
        invitation.revoked_at is not None
        or invitation.used_at is not None
        or invitation.status in {"revoked", "completed"}
        or invitation.expires_at <= now
    ):
        await session.execute(
            update(InvitationDeliveryJob)
            .where(InvitationDeliveryJob.id == job_id)
            .values(
                status=InvitationDeliveryStatus.FAILED,
                last_error="Invitation is not deliverable",
            )
        )
        await session.commit()
        return False

    await session.execute(
        update(InvitationDeliveryJob)
        .where(InvitationDeliveryJob.id == job_id)
        .values(status=InvitationDeliveryStatus.PROCESSING)
    )

    try:
        await send_message_stub(
            telegram_id=job.telegram_id,
            text=job.message_text,
        )
    except Exception as e:
        await session.execute(
            update(InvitationDeliveryJob)
            .where(InvitationDeliveryJob.id == job_id)
            .values(
                status=InvitationDeliveryStatus.FAILED,
                attempts=job.attempts + 1,
                last_error=str(e),
            )
        )
        await session.commit()
        return False

    await session.execute(
        update(InvitationDeliveryJob)
        .where(InvitationDeliveryJob.id == job_id)
        .values(
            status=InvitationDeliveryStatus.SENT,
            sent_at=now,
            last_error=None,
        )
    )

    await session.execute(
        update(Invitation)
        .where(Invitation.id == job.invitation_id)
        .values(
            status="sent",
            sent_at=now,
        )
    )

    await session.commit()
    return True


async def enqueue_pending_invitation_delivery_job(
    session: AsyncSession,
    job_id: int,
) -> str:
    from app.queue.rq import enqueue_invitation_delivery_job

    job = await session.get(InvitationDeliveryJob, job_id)
    if job is None:
        raise ValueError("Delivery job not found")

    if job.status != InvitationDeliveryStatus.PENDING:
        raise ValueError("Delivery job is not pending")

    rq_job = enqueue_invitation_delivery_job(job_id)
    now = dt.datetime.now(dt.UTC)

    await session.execute(
        update(InvitationDeliveryJob)
        .where(InvitationDeliveryJob.id == job_id)
        .values(
            status=InvitationDeliveryStatus.QUEUED,
            queued_at=now,
            last_error=None,
        )
    )
    await session.commit()

    return rq_job.id