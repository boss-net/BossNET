from core.entities.user import User, UserCreate
from core.services.auth_service import AuthenticationError, AuthService
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from infrastructure.container import container
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    roles: list[str]

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=user.roles,
        )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login."""
    auth_service = container.resolve(AuthService)

    try:
        user = await auth_service.authenticate_user(form_data.username, form_data.password)
        tokens = await auth_service.create_tokens(user.id)

        return {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token, "token_type": "bearer"}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    auth_service = container.resolve(AuthService)

    try:
        user = await auth_service.register_user(user_data)
        return UserResponse.from_domain(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/refresh-token", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh an access token."""
    auth_service = container.resolve(AuthService)

    try:
        tokens = await auth_service.refresh_access_token(refresh_token)

        return {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token, "token_type": "bearer"}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(container.resolve(AuthService).get_current_user)):
    """Get the current user."""
    return UserResponse.from_domain(current_user)
