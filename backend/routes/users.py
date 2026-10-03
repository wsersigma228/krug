from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from jose import jwt, ExpiredSignatureError, JWTError

from backend.config import SECRET_KEY, ALGORITHM
from backend.database import get_db
from backend.models import User, EmailDelivery
from backend.schemas import AccessTokenResponse, UserCreate, UserResponse, UserLogin, Token, TokenRefreshRequest
from backend.security import create_access_token, create_refresh_token, get_current_user, get_current_admin, verify_password, DUMMY_PASSWORD_HASH
from backend.crud import users as crud_users
from backend.rate_limit import check_rate_limit
from backend.account_tokens import issue_token, consume_token
from backend.schemas import EmailRequest, AccountTokenRequest, PasswordResetConfirm, NotificationSettings, LanguageSettings
from backend.security import get_password_hash

router = APIRouter()


@router.get("/verify-email", include_in_schema=False)
@router.get("/reset-password", include_in_schema=False)
def account_link_page():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent.parent.parent / "frontend" / "index.html", headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    })

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a user with a unique username and email."""
    await check_rate_limit(db, request, "register", user.username)
    db_user = await crud_users.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=409, detail="Username already exists")
    if user.email:
        db_email = await crud_users.get_user_by_email(db, email=user.email)
        if db_email:
            raise HTTPException(status_code=409, detail="Email already exists")
    try:
        return await crud_users.create_user(db=db, user_schemas=user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists")


@router.post("/login", response_model=Token)
async def login(user: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange credentials for access and refresh tokens."""
    await check_rate_limit(db, request, "login", user.username)
    db_user = await db.scalar(select(User).where(User.username == user.username).execution_options(populate_existing=True).with_for_update())
    password_valid = verify_password(
        user.password, db_user.hashed_password if db_user else DUMMY_PASSWORD_HASH
    )
    if not db_user or not password_valid:
        raise HTTPException(
            status_code=401, detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": db_user.username,
        "user_id": db_user.id,
        "version": db_user.token_version,
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(body: TokenRefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    await check_rate_limit(db, request, "refresh")
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != "refresh":
            raise credentials_exception
        user_id = payload.get("user_id")
        if type(user_id) is not int or not 1 <= user_id <= 2147483647:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Refresh token expired",
            headers={"WWW-Authenticate": "Bearer"}
            )
    except (JWTError, ValueError, TypeError, OverflowError):
        raise credentials_exception

    result = await db.execute(select(User).filter(User.id == user_id).execution_options(populate_existing=True).with_for_update())
    db_user = result.scalars().first()
    if db_user is None or type(payload.get("version")) is not int or payload["version"] != db_user.token_version:
        raise credentials_exception

    token_data = {
        "sub": db_user.username,
        "user_id": db_user.id,
        "version": db_user.token_version,
    }
    new_access_token = create_access_token(data=token_data)

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/users/get", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all users. Admin only."""
    return await crud_users.get_all_users(db)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete your account, or any account as an admin."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    success = await crud_users.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Return your profile."""
    return current_user


@router.get("/admin/panel")
def admin_panel(current_admin: User = Depends(get_current_admin)):
    """Check admin access."""
    return {"message": "Welcome to the admin panel!", "admin_name": current_admin.username}


@router.post("/auth/email-verification/request", status_code=202)
async def request_verification(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    version = current_user.token_version
    await check_rate_limit(db, request, "verify-request", str(current_user.id))
    user = await db.scalar(select(User).where(User.id == current_user.id).execution_options(populate_existing=True).with_for_update())
    if not user or user.token_version != version:
        raise HTTPException(401, "Session revoked")
    if not user.email:
        raise HTTPException(400, "Account has no email")
    if not user.email_verified:
        await issue_token(db, user, "verify")
    await db.commit()
    return {"message": "Verification requested"}


@router.post("/auth/email-verification/confirm", status_code=204)
async def confirm_verification(body: AccountTokenRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(db, request, "verify-confirm")
    user = await consume_token(db, body.token, "verify")
    user.email_verified = True
    await db.commit()


@router.post("/auth/password-reset/request", status_code=202)
async def request_reset(body: EmailRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(db, request, "reset-request", body.email)
    user = await db.scalar(select(User).where(User.email == body.email).with_for_update())
    if user:
        await issue_token(db, user, "reset")
    await db.commit()
    return {"message": "If the account exists, a reset email will be sent"}


@router.post("/auth/password-reset/confirm", status_code=204)
async def confirm_reset(body: PasswordResetConfirm, request: Request, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(db, request, "reset-confirm")
    user = await consume_token(db, body.token, "reset")
    user.hashed_password = get_password_hash(body.password)
    user.token_version += 1
    await db.commit()


@router.post("/logout", status_code=204)
async def logout(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    version = current_user.token_version
    await check_rate_limit(db, request, "logout", str(current_user.id))
    user = await db.scalar(select(User).where(User.id == current_user.id).execution_options(populate_existing=True).with_for_update())
    if not user or user.token_version != version:
        raise HTTPException(401, "Session revoked")
    user.token_version += 1
    await db.commit()


@router.get("/me/notifications", response_model=NotificationSettings)
async def notification_settings(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/notifications", response_model=NotificationSettings)
async def change_notification_settings(body: NotificationSettings, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    version = current_user.token_version
    user = await db.scalar(select(User).where(User.id == current_user.id)
                           .execution_options(populate_existing=True).with_for_update())
    if not user or user.token_version != version:
        raise HTTPException(401, "Session revoked")
    if body.email_publications and (not user.email or not user.email_verified):
        raise HTTPException(403, "Verify your email before enabling notifications")
    user.email_publications = body.email_publications
    if not body.email_publications:
        await db.execute(update(EmailDelivery).where(
            EmailDelivery.recipient_id == user.id, EmailDelivery.kind == "publication",
            EmailDelivery.status == "pending",
        ).values(status="cancelled"))
    await db.commit()
    return user


@router.patch("/me/language", response_model=LanguageSettings)
async def change_language(body: LanguageSettings, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user), initialize: bool = False):
    version = current_user.token_version
    user = await db.scalar(select(User).where(User.id == current_user.id)
                           .execution_options(populate_existing=True).with_for_update())
    if not user or user.token_version != version:
        raise HTTPException(401, "Session revoked")
    # A first visit must not overwrite an explicit choice made on another device.
    if not initialize or user.language is None:
        user.language = body.language
    await db.commit()
    return user
