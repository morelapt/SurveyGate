import datetime as dt

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invitation, Segment, Survey, SurveySend, User, UserIdentity
from app.services.delivery import send_message_stub
from app.services.invitations_tokens import generate_token, hash_token
from app.services.segments_compiler import compile_segment_query


class SendSummary(dict):
    # просто удобный тип-ярлык (не обязателен)
    pass


async def send_invitations(
    session: AsyncSession,
    survey_id: int,
    segment_id: int,
    message_template: str,
    ttl_days: int = 14,
    limit: int = 200,
) -> dict:
    """
    Главный use-case:
    - валидируем survey/segment
    - выбираем пользователей по segment
    - revoke+new для активных инвайтов
    - создаём invitation + генерим ссылку + stub-delivery
    - возвращаем summary
    """
    survey = await session.get(Survey, survey_id)
    if not survey:
        raise ValueError("Survey not found")
    if survey.status == "closed":
        raise ValueError("Survey is closed")

    segment = await session.get(Segment, segment_id)
    if not segment:
        raise ValueError("Segment not found")

    now = dt.datetime.now(dt.UTC)
    expires_at = now + dt.timedelta(days=ttl_days)

    # фиксируем сам запуск как сущность (красиво для портфолио)
    send_stmt = (
        insert(SurveySend)
        .values(
            survey_id=survey_id,
            segment_id=segment_id,
            message_template=message_template,
            ttl_days=ttl_days,
            created_at=now,
        )
        .returning(SurveySend.id)
    )
    send_res = await session.execute(send_stmt)
    send_id = send_res.scalar_one()

    # выбрать пользователей по сегменту
    users_stmt = compile_segment_query(segment.filters).limit(limit)
    users_res = await session.execute(users_stmt)
    users = users_res.scalars().all()

    targeted = len(users)
    created = 0
    resent = 0
    skipped = 0

    for user in users:
        # достаём telegram_id (если нет identity — пропустим)
        tid_stmt = select(UserIdentity.telegram_id).where(UserIdentity.user_id == user.id)
        tid_res = await session.execute(tid_stmt)
        telegram_id = tid_res.scalar_one_or_none()
        if telegram_id is None:
            skipped += 1
            continue

        # найти активный инвайт на этот survey+user
        active_stmt = select(Invitation).where(
            Invitation.survey_id == survey_id,
            Invitation.user_id == user.id,
            Invitation.revoked_at.is_(None),
            Invitation.used_at.is_(None),
        )
        active_res = await session.execute(active_stmt)
        active = active_res.scalar_one_or_none()

        if active:
            # стратегия: revoke + new
            await session.execute(
                update(Invitation)
                .where(Invitation.id == active.id)
                .values(revoked_at=now, status="revoked", resend_count=active.resend_count + 1)
            )
            resent += 1

        # создать новый инвайт
        token = generate_token()
        token_h = hash_token(token)

        inv_stmt = (
            insert(Invitation)
            .values(
                survey_id=survey_id,
                user_id=user.id,
                send_id=send_id,
                token_hash=token_h,
                created_at=now,
                expires_at=expires_at,
                status="queued",
            )
            .returning(Invitation.id)
        )
        inv_res = await session.execute(inv_stmt)
        invitation_id = inv_res.scalar_one()

        link = f"/s/{survey_id}/{token}"
        text = message_template.replace("{link}", link)

        await send_message_stub(telegram_id=telegram_id, text=text)

        # отметить как sent
        await session.execute(
            update(Invitation)
            .where(Invitation.id == invitation_id)
            .values(sent_at=now, status="sent")
        )

        created += 1

    await session.commit()

    return {
        "send_id": send_id,
        "targeted": targeted,
        "created": created,
        "resent": resent,
        "skipped": skipped,
    }
