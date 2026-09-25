from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.time import now_utc
from app.models.user import RefreshToken, User
from app.schemas.auth import TokenPair
from app.services import audit_service

# Used when the email is unknown so that a failed login takes the same time as a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password")


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email))).unique().scalar_one_or_none()


async def authenticate(db: AsyncSession, *, email: str, password: str, ip: str | None) -> User:
    user = await get_user_by_email(db, email)
    password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)

    if user is None or not password_ok:
        audit_service.record(db, user_id=None, action="LOGIN_FAILED", details={"email": email}, ip_address=ip)
        await db.commit()
        raise UnauthorizedError("Invalid email or password", code="invalid_credentials")

    if not user.is_active:
        audit_service.record(db, user_id=user.id, action="LOGIN_FAILED", details={"reason": "inactive"}, ip_address=ip)
        await db.commit()
        raise UnauthorizedError("This account is deactivated", code="account_inactive")

    user.last_login_at = now_utc()
    audit_service.record(db, user_id=user.id, action="LOGIN", entity_type="user", entity_id=str(user.id), ip_address=ip)
    return user


async def issue_tokens(db: AsyncSession, user: User, *, user_agent: str | None) -> TokenPair:
    access_token, expires_in = create_access_token(user_id=user.id, role=user.role.value)
    refresh_token, jti, expires_at = create_refresh_token(user_id=user.id, role=user.role.value)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at, user_agent=(user_agent or "")[:255] or None))
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


async def refresh_tokens(db: AsyncSession, refresh_token: str, *, user_agent: str | None) -> tuple[TokenPair, User]:
    payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    stored = (await db.execute(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))).scalar_one_or_none()
    if stored is None:
        raise UnauthorizedError("Refresh token is not recognised", code="invalid_refresh_token")

    if stored.revoked_at is not None:
        # A revoked token being presented again suggests it was stolen: drop every session for this user.
        await revoke_all_for_user(db, stored.user_id)
        await db.commit()
        raise UnauthorizedError("Refresh token has been revoked", code="invalid_refresh_token")

    if stored.expires_at <= now_utc():
        raise UnauthorizedError("Refresh token has expired", code="token_expired")

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("This account is deactivated", code="account_inactive")

    stored.revoked_at = now_utc()
    tokens = await issue_tokens(db, user, user_agent=user_agent)
    return tokens, user


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH, verify_exp=False)
    except UnauthorizedError:
        return  # Nothing to revoke; logout still succeeds for the client.
    stored = (await db.execute(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))).scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = now_utc()


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )


async def logout(db: AsyncSession, user: User, refresh_token: str | None, *, ip: str | None) -> None:
    if refresh_token:
        await revoke_refresh_token(db, refresh_token)
    audit_service.record(db, user_id=user.id, action="LOGOUT", entity_type="user", entity_id=str(user.id), ip_address=ip)
    await db.commit()


async def change_password(
    db: AsyncSession, user: User, *, current_password: str, new_password: str, ip: str | None
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise BadRequestError("Current password is incorrect", code="invalid_password")
    if current_password == new_password:
        raise BadRequestError("New password must differ from the current password", code="same_password")

    user.password_hash = hash_password(new_password)
    await revoke_all_for_user(db, user.id)
    audit_service.record(
        db, user_id=user.id, action="PASSWORD_CHANGED", entity_type="user", entity_id=str(user.id), ip_address=ip
    )
    await db.commit()
