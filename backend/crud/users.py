from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models import Community, Event, Post, Project, Team, User
from fastapi import HTTPException
from backend.media import delete_photo
from backend.schemas import UserCreate
from backend.security import get_password_hash


async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()


async def create_user(db: AsyncSession, user_schemas: UserCreate):
    """Hash the password before storing the account."""
    hashed_password = get_password_hash(user_schemas.password)
    new_user = User(
        username=user_schemas.username,
        email=user_schemas.email,
        language=user_schemas.language,
        hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def delete_user(db: AsyncSession, user_id: int):
    """Delete the account and its posts and subscriptions."""
    # Block new Post FK references before collecting the files to remove.
    result = await db.execute(select(User).filter(User.id == user_id)
                              .execution_options(populate_existing=True).with_for_update())
    db_user = result.scalars().first()
    if db_user:
        if await db.scalar(select(Project.id).where(Project.owner_id == user_id).limit(1)) or \
           await db.scalar(select(Team.id).where(Team.owner_id == user_id).limit(1)) or \
           await db.scalar(select(Community.id).where(Community.owner_id == user_id).limit(1)) or \
           await db.scalar(select(Event.id).where(Event.owner_id == user_id).limit(1)):
            raise HTTPException(409, "Account owns public entities and cannot be deleted")
        keys = list(await db.scalars(select(Post.image_key).where(Post.author_id == user_id)
                                    .order_by(Post.id).with_for_update()))
        avatar_key = db_user.avatar_key
        await db.delete(db_user)
        await db.commit()
        delete_photo(avatar_key)
        for key in keys:
            delete_photo(key)
        return True
    return False
