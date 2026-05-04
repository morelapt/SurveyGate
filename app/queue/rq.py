from rq import Queue
from rq.job import Job

from app.queue.jobs import rq_process_invitation_delivery_job
from app.queue.redis_client import get_redis_connection

DELIVERY_QUEUE_NAME = "invitation_delivery"


def get_delivery_queue() -> Queue:
    return Queue(
        name=DELIVERY_QUEUE_NAME,
        connection=get_redis_connection(),
    )


def enqueue_invitation_delivery_job(job_id: int) -> Job:
    queue = get_delivery_queue()
    return queue.enqueue(rq_process_invitation_delivery_job, job_id)