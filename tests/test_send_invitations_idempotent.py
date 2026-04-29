import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invitation, InvitationDeliveryJob, InvitationDeliveryStatus
from app.services.send_invitations import send_invitations

pytestmark = pytest.mark.asyncio

async def test_send_invitations_revokes_previous_active(
    session: AsyncSession,
    make_user_with_identity,
    make_survey,
    make_segment_city_eq,
):
    # arrange
    user = await make_user_with_identity(city="Moscow", age=25, has_children=False)
    survey = await make_survey(title="S1")
    segment = await make_segment_city_eq(name="seg", city="Moscow")

    payload = dict(
        survey_id=survey.id,
        segment_id=segment.id,
        message_template="Hi {link}",
        ttl_days=14,
        limit=200,
    )

    # act 1
    r1 = await send_invitations(session=session, **payload)
    assert r1["created"] == 1

    invs1 = (
        (
            await session.execute(
                select(Invitation)
                .where(
                    Invitation.survey_id == survey.id,
                    Invitation.user_id == user.id,
                )
                .order_by(Invitation.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(invs1) == 1

    first = invs1[0]
    assert first.revoked_at is None
    assert first.used_at is None
    assert first.status == "queued"

    # act 2
    r2 = await send_invitations(session=session, **payload)
    assert r2["created"] == 1
    assert r2["resent"] == 1

    invs2 = (
        (
            await session.execute(
                select(Invitation)
                .where(
                    Invitation.survey_id == survey.id,
                    Invitation.user_id == user.id,
                )
                .order_by(Invitation.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(invs2) == 2

    old, new = invs2[0], invs2[1]

    # old invitation is revoked
    assert old.revoked_at is not None
    assert old.status == "revoked"

    # new invitation is active and waiting for delivery
    assert new.revoked_at is None
    assert new.used_at is None
    assert new.status == "queued"

    # token changed
    assert old.token_hash != new.token_hash

    # "one active invite" invariant
    active = [i for i in invs2 if i.revoked_at is None and i.used_at is None]
    assert len(active) == 1

    # new invitation has a queued delivery job
    delivery_job = (
        await session.execute(
            select(InvitationDeliveryJob).where(
                InvitationDeliveryJob.invitation_id == new.id,
            )
        )
    ).scalar_one()

    assert delivery_job.status == InvitationDeliveryStatus.QUEUED