from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenType, decode_token
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Not authenticated", code="not_authenticated")

    payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid token", code="invalid_token") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is inactive or no longer exists", code="account_inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action", code="forbidden")
        return user

    return dependency


HRUser = Annotated[User, Depends(require_roles(UserRole.HR))]


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


ClientIP = Annotated[str | None, Depends(client_ip)]
