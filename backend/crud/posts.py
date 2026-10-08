from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from backend.models import Community, CommunityMember, Post, Subscription, User, EmailDelivery, Project, ProjectMember
from backend.project_access import public_post
from fastapi import HTTPException
from datetime import datetime, timezone
from backend.schemas import PostCreate, PostUpdate
from sqlalchemy import func, or_, update
from backend.pagination import Cursor, seek_page
from uuid import uuid4
from backend.media import delete_photo


async def record_publication_emails(db: AsyncSession, post: Post) -> None:
    """Persist deliveries in the publication transaction, without contacting Redis."""
    # Project updates have no email audience yet; avoid exposing private project content.
    if post.project_id is not None or post.community_id is not None:
        return
    # ponytail: fanout loads recipient IDs; use INSERT ... SELECT for large follower counts.
    recipients = await db.scalars(
        select(User.id).join(Subscription, Subscription.subscriber_id == User.id)
        .where(Subscription.author_id == post.author_id, User.email.is_not(None), User.email != "",
               User.email_verified.is_(True), User.email_publications.is_(True))
        .order_by(User.id)
        # Non-key locks serialize preferences but remain compatible with Post FK checks.
        .with_for_update(of=User, key_share=True)
    )
    publication_id = str(uuid4())
    db.add_all([
        EmailDelivery(publication_id=publication_id, post_id=post.id, recipient_id=user_id)
        for user_id in recipients
    ])


async def get_post(db: AsyncSession, post_id: int, user_id: int | None = None):
    """Without user_id, this is an internal lookup that includes drafts."""
    query = select(Post).filter(Post.id == post_id)
    if user_id is not None:
        query = query.filter(Post.author_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_published_post(db: AsyncSession, post_id: int):
    """Look up a post that is safe to expose publicly."""
    result = await db.execute(
        select(Post).where(Post.id == post_id, public_post())
    )
    return result.scalar_one_or_none()


async def get_user_posts(
    db: AsyncSession,
    user_id: int,
    is_published: bool | None = None,
    limit: int = 100,
    cursor: Cursor | None = None,
    public_only: bool = False,
):
    """Fetch an author's posts, including one row beyond the page."""
    query = select(Post).filter(Post.author_id == user_id)
    if is_published is not None:
        query = query.filter(Post.is_published.is_(is_published))
    if public_only:
        query = query.where(public_post())
    query = seek_page(query, Post, cursor, limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_feed(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    cursor: Cursor | None = None,
):
    """Fetch published posts from followed authors, plus one extra row."""
    subquery = (
        select(Subscription.author_id)
        .filter(Subscription.subscriber_id == user_id)
    )
    query = (
        select(Post)
        .filter(
            Post.author_id.in_(subquery),
            public_post(),
        )
        .options(joinedload(Post.author))
    )
    query = seek_page(query, Post, cursor, limit)
    result = await db.execute(query)
    return result.scalars().unique().all()


async def create_post(
    db: AsyncSession,
    post_data: PostCreate,
    author_id: int,
):
    if post_data.project_id is not None or post_data.community_id is not None:
        author_exists = await db.scalar(select(User.id).where(User.id == author_id)
                                        .with_for_update(read=True, key_share=True))
        if author_exists is None:
            raise HTTPException(401, "Account no longer exists")
        if post_data.project_id is not None:
            project = await db.scalar(select(Project).where(Project.id == post_data.project_id).with_for_update())
            if project is None:
                raise HTTPException(404, "Project not found")
            is_member = await db.scalar(select(ProjectMember.id).where(
                ProjectMember.project_id == project.id, ProjectMember.user_id == author_id))
            if project.owner_id != author_id and not is_member:
                raise HTTPException(404, "Project not found")
            if post_data.is_published and project.visibility == "public":
                project.last_activity_at = datetime.now(timezone.utc)
    if post_data.community_id is not None:
        community = await db.scalar(select(Community).where(Community.id == post_data.community_id)
                                    .execution_options(populate_existing=True).with_for_update())
        if community is None:
            raise HTTPException(404, "Community not found")
        member = await db.scalar(select(CommunityMember.id).where(
            CommunityMember.community_id == community.id, CommunityMember.user_id == author_id))
        if community.owner_id != author_id and not member:
            if community.visibility != "public":
                raise HTTPException(404, "Community not found")
            raise HTTPException(403, "Join the community before creating posts")
        if post_data.is_published and (community.visibility != "public" or not member):
            raise HTTPException(403, "Join the public community before publishing")
    new_post = Post(
        title=post_data.title,
        content=post_data.content,
        is_published=post_data.is_published,
        author_id=author_id,
        project_id=post_data.project_id,
        community_id=post_data.community_id,
    )
    db.add(new_post)
    if new_post.is_published:
        await db.flush()
        await record_publication_emails(db, new_post)
    await db.commit()
    await db.refresh(new_post)
    return new_post


async def update_post(
    db: AsyncSession,
    post_id: int,
    user_id: int,
    post_data: PostUpdate,
):
    """Lock a community first, then the post, so membership edits are serialized."""
    update_dict = post_data.model_dump(exclude_unset=True)
    actor = await db.scalar(select(User.id).where(User.id == user_id)
                             .with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    current_community_id = await db.scalar(select(Post.community_id).where(
        Post.id == post_id, Post.author_id == user_id))
    if current_community_id is not None:
        community = await db.scalar(select(Community).where(Community.id == current_community_id)
                                    .execution_options(populate_existing=True).with_for_update())
        if community is None:
            raise HTTPException(404, "Community not found")
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.author_id == user_id)
        .execution_options(populate_existing=True).with_for_update()
    )
    post = result.scalar_one_or_none()
    if not post:
        return None

    was_published = post.is_published

    if post.community_id != current_community_id:
        raise HTTPException(409, "Post entity changed; reload and retry")
    if current_community_id is not None:
        member = await db.scalar(select(CommunityMember.id).where(
            CommunityMember.community_id == community.id, CommunityMember.user_id == user_id))
        if not member:
            raise HTTPException(403, "Join the community before editing its posts")
        if update_dict.get("is_published", post.is_published) and community.visibility != "public":
            raise HTTPException(403, "Only public communities can have published posts")
    for key, value in update_dict.items():
        setattr(post, key, value)

    became_published = not was_published and post.is_published
    if post.project_id is not None and post.is_published and (
        became_published or "title" in update_dict or "content" in update_dict
    ):
        await db.execute(update(Project).where(Project.id == post.project_id, Project.visibility == "public")
                         .values(last_activity_at=datetime.now(timezone.utc)))
    if became_published:
        await record_publication_emails(db, post)
    elif was_published and not post.is_published:
        await db.execute(update(EmailDelivery).where(
            EmailDelivery.post_id == post.id, EmailDelivery.status == "pending",
        ).values(status="cancelled"))
    await db.commit()
    await db.refresh(post)
    return post, became_published


async def delete_post(db: AsyncSession, post_id: int, user_id: int):
    """Delete an owned post or one moderated by its community owner."""
    actor = await db.scalar(select(User.id).where(User.id == user_id)
                            .with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    community_id = await db.scalar(select(Post.community_id).where(Post.id == post_id, or_(
        Post.author_id == user_id,
        Post.community_id.in_(select(Community.id).where(Community.owner_id == user_id)))))
    if community_id is not None:
        await db.scalar(select(Community.id).where(Community.id == community_id).with_for_update())
    post = await db.scalar(select(Post).where(Post.id == post_id, or_(
        Post.author_id == user_id,
        Post.community_id.in_(select(Community.id).where(Community.owner_id == user_id))))
                           .execution_options(populate_existing=True).with_for_update())
    if not post:
        return False
    key = post.image_key
    await db.delete(post)
    await db.commit()
    delete_photo(key)
    return True


async def get_subscriber_count(db: AsyncSession, author_id: int) -> int:
    result = await db.execute(
        select(func.count(Subscription.id)).filter(Subscription.author_id == author_id)
    )
    return result.scalar() or 0
