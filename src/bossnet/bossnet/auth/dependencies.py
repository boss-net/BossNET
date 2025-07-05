from typing import List, Optional

from auth.models import UserInDB, UserRole
from auth.service import AuthService
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import settings

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def get_auth_service():
    return AuthService(secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), auth_service: AuthService = Depends(get_auth_service), db=Depends(get_db)
) -> UserInDB:
    return await auth_service.get_current_user(token, db)


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user), auth_service: AuthService = Depends(get_auth_service)
) -> UserInDB:
    return await auth_service.get_current_active_user(current_user)


def has_required_roles(required_roles: Optional[List[UserRole]] = None):
    """Dependency to check if user has any of the required roles"""

    async def role_checker(
        current_user: UserInDB = Depends(get_current_active_user), auth_service: AuthService = Depends(get_auth_service)
    ) -> UserInDB:
        has_access = auth_service.has_required_roles(current_user, required_roles or [])
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to access this resource")
        return current_user

    return role_checker


# Common role dependencies
async def admin_required(
    current_user: UserInDB = Depends(get_current_active_user), auth_service: AuthService = Depends(get_auth_service)
) -> UserInDB:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


async def teacher_or_admin_required(
    current_user: UserInDB = Depends(get_current_active_user), auth_service: AuthService = Depends(get_auth_service)
) -> UserInDB:
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher or admin privileges required")
    return current_user
