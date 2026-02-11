import logging

logger = logging.getLogger("app.delivery")


async def send_message_stub(telegram_id: int, text: str) -> None:
    logger.info("DELIVERY STUB telegram_id=%s text=%s", telegram_id, text)
