from fastapi import APIRouter, Request, status

from app.api.deps import DB, ClientIP, CurrentUser
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UpdateLanguageRequest,
    UserResponse,
)
from app.schemas.common import Message
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: DB, request: Request, ip: ClientIP) -> LoginResponse:
    user = await auth_service.authenticate(db, email=payload.email, password=payload.password, ip=ip)
    tokens = await auth_service.issue_tokens(db, user, user_agent=request.headers.get("user-agent"))
    return LoginResponse(**tokens.model_dump(), user=UserResponse.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DB, request: Request) -> TokenPair:
    tokens, _ = await auth_service.refresh_tokens(
        db, payload.refresh_token, user_agent=request.headers.get("user-agent")
    )
    return tokens


@router.post("/logout", response_model=Message)
async def logout(payload: LogoutRequest, db: DB, user: CurrentUser, ip: ClientIP) -> Message:
    await auth_service.logout(db, user, payload.refresh_token, ip=ip)
    return Message(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.put("/me/language", response_model=UserResponse)
async def update_language(payload: UpdateLanguageRequest, db: DB, user: CurrentUser) -> UserResponse:
    user.preferred_language = payload.preferred_language
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=Message, status_code=status.HTTP_200_OK)
async def change_password(payload: ChangePasswordRequest, db: DB, user: CurrentUser, ip: ClientIP) -> Message:
    await auth_service.change_password(
        db, user, current_password=payload.current_password, new_password=payload.new_password, ip=ip
    )
    return Message(message="Password changed. Please sign in again.")
