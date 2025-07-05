"""
Authentication endpoints
"""

from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from src.application.services.auth_service import AuthService
from src.infrastructure.container import Container
from src.interfaces.api.v1.schemas.token import Token, TokenRefresh
from src.interfaces.api.v1.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
@inject
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(Provide[Container.auth_service])
) -> Any:
    """Login endpoint"""
    try:
        token_data = await auth_service.authenticate_user(email=form_data.username, password=form_data.password)
        return token_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=Token)
@inject
async def refresh_token(token_data: TokenRefresh, auth_service: AuthService = Depends(Provide[Container.auth_service])) -> Any:
    """Refresh access token"""
    try:
        new_token_data = await auth_service.refresh_access_token(token_data.refresh_token)
        return new_token_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)
@inject
async def register(user_data: UserCreate, auth_service: AuthService = Depends(Provide[Container.auth_service])) -> Any:
    """User registration endpoint"""
    try:
        user = await auth_service.register_user(
            email=user_data.email, password=user_data.password, full_name=user_data.full_name
        )
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout")
@inject
async def logout(token_data: TokenRefresh, auth_service: AuthService = Depends(Provide[Container.auth_service])) -> Any:
    """Logout endpoint - invalidate refresh token"""
    try:
        await auth_service.logout_user(token_data.refresh_token)
        return {"message": "Successfully logged out"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
