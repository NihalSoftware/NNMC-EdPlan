import logging

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.security.auth import hash_password, verify_password
from app.student.domains.auth.repositories import user_repository
from app.student.domains.auth.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    try:
        return await user_repository.get_by_email(db, email)
    except SQLAlchemyError as exc:
        logger.exception("Database error while fetching user by email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error"
        ) from exc


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = await user_repository.create_user(
        db,
        email=payload.email.lower(),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        role=UserRole.CUSTOMER.value,
        password_hash=hash_password(payload.password),
    )
    try:
        await user_repository.save(db, user)
    except IntegrityError as exc:
        await db.rollback()
        logger.exception("Integrity error while registering user email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database error while registering user email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error"
        ) from exc
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email.lower())
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await user_repository.update_last_login(db, user, func.now())
    try:
        await user_repository.save(db, user)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database error while updating last_login_at email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error"
        ) from exc
    return user
