import datetime as dt

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invitation, Response
from app.services.invitations_tokens import hash_token


def _validate_invitation_state(invitation: Invitation, now: dt.datetime) -> None:
    if invitation.revoked_at is not None:
        raise ValueError("Invitation revoked")
    if invitation.used_at is not None:
        raise ValueError("Invitation already used")
    if invitation.expires_at <= now:
        raise ValueError("Invitation expired")


async def _get_invitation_by_token(
    session: AsyncSession,
    survey_id: int,
    token: str,
) -> Invitation:
    token_h = hash_token(token)

    stmt = select(Invitation).where(
        Invitation.survey_id == survey_id,
        Invitation.token_hash == token_h,
    )
    res = await session.execute(stmt)
    invitation = res.scalar_one_or_none()

    if invitation is None:
        raise ValueError("Invitation not found")

    return invitation


async def get_public_invitation_status(
    session: AsyncSession,
    survey_id: int,
    token: str,
) -> dict:
    now = dt.datetime.now(dt.UTC)
    invitation = await _get_invitation_by_token(
        session=session,
        survey_id=survey_id,
        token=token,
    )

    _validate_invitation_state(invitation, now)

    if invitation.status == "sent":
        await session.execute(
            update(Invitation)
            .where(Invitation.id == invitation.id)
            .values(status="opened")
        )
        await session.commit()
        current_status = "opened"
    else:
        current_status = invitation.status

    return {
        "survey_id": survey_id,
        "invitation_id": invitation.id,
        "status": current_status,
    }


async def submit_public_response(
    session: AsyncSession,
    survey_id: int,
    token: str,
    answers: dict,
) -> int:
    now = dt.datetime.now(dt.UTC)
    invitation = await _get_invitation_by_token(
        session=session,
        survey_id=survey_id,
        token=token,
    )

    _validate_invitation_state(invitation, now)

    response_stmt = (
        insert(Response)
        .values(
            survey_id=survey_id,
            user_id=invitation.user_id,
            invitation_id=invitation.id,
            answers=answers,
            submitted_at=now,
        )
        .returning(Response.id)
    )
    response_res = await session.execute(response_stmt)
    response_id = response_res.scalar_one()

    await session.execute(
        update(Invitation)
        .where(Invitation.id == invitation.id)
        .values(
            used_at=now,
            status="completed",
        )
    )

    await session.commit()
    return response_id