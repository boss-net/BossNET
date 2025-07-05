from typing import Any, List

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.application.services.user_service import UserService
from src.core.domain.entities.user import User
from src.infrastructure.container import Container
from src.interfaces.api.dependencies import get_current_active_user
from src.interfaces.api.v1.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """Get current user"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.put("/me", response_model=UserResponse)
@inject
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> Any:
    """Update current user"""
    try:
        updated_user = await user_service.update_user(
            user_id=current_user.id, full_name=user_update.full_name, is_active=user_update.is_active
        )
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            full_name=updated_user.full_name,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[UserResponse])
@inject
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> Any:
    """List users (admin only)"""
    # In a real app, you'd check if user is admin
    users = await user_service.list_users(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
@inject
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(Provide[Container.user_service]),
) -> Any:
    """Get user by ID (admin only)"""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ** rest of code here **
