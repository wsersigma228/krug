from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models import User, Post
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
        keys = list(await db.scalars(select(Post.image_key).where(Post.author_id == user_id)
                                    .order_by(Post.id).with_for_update()))
        await db.delete(db_user)
        await db.commit()
        for key in keys:
            delete_photo(key)
        return True
    return False
