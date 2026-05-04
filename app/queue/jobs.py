import asyncio

from app.db.session import SessionFactory
from app.services.delivery_jobs import process_invitation_delivery_job


async def _run_process_invitation_delivery_job(job_id: int) -> bool:
    async with SessionFactory() as session:
        return await process_invitation_delivery_job(
            session=session,
            job_id=job_id,
        )


def rq_process_invitation_delivery_job(job_id: int) -> bool:
    return asyncio.run(_run_process_invitation_delivery_job(job_id))