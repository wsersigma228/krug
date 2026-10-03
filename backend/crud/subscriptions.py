from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sa_delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from backend.models import Subscription, User, EmailDelivery, Post
from backend.pagination import Cursor, seek_page


async def subscribe(
    db: AsyncSession,
    subscriber_id: int,
    author_id: int,
) -> Subscription | None:
    """Return None for self-subscription, duplicates or a missing author."""
    if subscriber_id == author_id:
        return None

    existing = await db.execute(
        select(Subscription).filter(
            Subscription.subscriber_id == subscriber_id,
            Subscription.author_id == author_id,
        )
    )
    if existing.scalars().first():
        return None

    author_check = await db.execute(select(User).filter(User.id == author_id))
    if not author_check.scalars().first():
        return None

    sub = Subscription(subscriber_id=subscriber_id, author_id=author_id)
    db.add(sub)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None

    await db.refresh(sub)
    return sub


async def unsubscribe(
    db: AsyncSession,
    subscriber_id: int,
    author_id: int,
) -> bool:
    """Return whether a subscription was removed."""
    result = await db.execute(
        sa_delete(Subscription).where(
            Subscription.subscriber_id == subscriber_id,
            Subscription.author_id == author_id,
        )
    )
    await db.execute(update(EmailDelivery).where(
        EmailDelivery.recipient_id == subscriber_id,
        EmailDelivery.post_id.in_(select(Post.id).where(Post.author_id == author_id)),
        EmailDelivery.status == "pending",
    ).values(status="cancelled"))
    await db.commit()
    return result.rowcount > 0


async def get_subscribed_authors(
    db: AsyncSession,
    subscriber_id: int,
) -> list[User]:
    """Return all followed authors for internal callers."""
    result = await db.execute(
        select(User)
        .join(Subscription, Subscription.author_id == User.id)
        .filter(Subscription.subscriber_id == subscriber_id)
    )
    return result.scalars().all()


async def get_subscribers(
    db: AsyncSession,
    author_id: int,
) -> list[User]:
    """Return every subscriber for internal callers."""
    result = await db.execute(
        select(User)
        .join(Subscription, Subscription.subscriber_id == User.id)
        .filter(Subscription.author_id == author_id)
    )
    return result.scalars().all()


async def is_subscribed(
    db: AsyncSession,
    subscriber_id: int,
    author_id: int,
) -> bool:
    result = await db.execute(
        select(Subscription).filter(
            Subscription.subscriber_id == subscriber_id,
            Subscription.author_id == author_id,
        )
    )
    return result.scalars().first() is not None


async def get_subscription_page(
    db: AsyncSession,
    user_id: int,
    *,
    followers: bool = False,
    limit: int = 100,
    cursor: Cursor | None = None,
) -> list[Subscription]:
    # Page by the follow event, not the user's account creation time.
    owner = Subscription.author_id if followers else Subscription.subscriber_id
    related_user = Subscription.subscriber if followers else Subscription.author
    query = select(Subscription).where(owner == user_id).options(joinedload(related_user))
    result = await db.execute(seek_page(query, Subscription, cursor, limit))
    return list(result.scalars().all())
