from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import ExpiredSignatureError, JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from backend.database import get_db
from backend.models import User

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
pwd_context = PasswordHash((Argon2Hasher(), BcryptHasher()))
DUMMY_PASSWORD_HASH = pwd_context.hash("dummy-password-for-login-timing")


def get_password_hash(password: str) -> str:
    """Use Argon2 for new passwords."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Accept Argon2 and legacy bcrypt hashes."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict):
    """Issue an access token for API requests."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """Issue a token accepted only by /refresh."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
):
    """Require an access token belonging to an existing user."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("token_type")
        if token_type != "access":
            raise credentials_exception
        user_id = payload.get("user_id")
        if type(user_id) is not int or not 1 <= user_id <= 2147483647:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except (JWTError, ValueError, TypeError, OverflowError):
        raise credentials_exception

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if type(payload.get("version")) is not int or payload["version"] != user.token_version:
        raise credentials_exception
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the admin role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

async def get_optional_user(
    authorization: str | None = Header(default=None),
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        if authorization is not None:
            raise HTTPException(status_code=401, detail="Invalid authorization header", headers={"WWW-Authenticate": "Bearer"})
        return None
    return await get_current_user(credentials=credentials, db=db)
