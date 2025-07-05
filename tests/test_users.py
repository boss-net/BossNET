"""Test cases for user management functionality."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.sqlalchemy.models.user import UserModel
from src.utils.security_utils import hash_password


async def create_test_user(
    session: AsyncSession, email: str = "test@example.com", password: str = "password123", is_active: bool = True
) -> UserModel:
    """Create a test user in the database.

    Args:
        session: Database session
        email: User's email address
        password: User's password
        is_active: User's active status

    Returns:
        UserModel: The created user
    """
    user = UserModel(
        email=email,
        hashed_password=hash_password(password),
        full_name="Test User" if not email.startswith("user") else f"User {email.split('@')[0]}",
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_auth_headers(
    async_client: AsyncClient, email: str = "test@example.com", password: str = "password123"
) -> dict[str, str]:
    """Get authentication headers for API requests.

    Args:
        async_client: Test client
        email: User's email for authentication
        password: User's password

    Returns:
        dict: Authorization headers
    """
    login_data = {"username": email, "password": password, "grant_type": "password"}
    response = await async_client.post("/api/v1/auth/login", data=login_data)
    tokens = response.json()

    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test getting current user info.

    Verifies that an authenticated user can retrieve their own profile.
    """
    # Create test user
    user = await create_test_user(db_session)

    # Get auth headers
    headers = await get_auth_headers(async_client, user.email)

    # Get current user
    response = await async_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == user.email, f"Expected email {user.email}, got {data['email']}"
    assert data["full_name"] == user.full_name


@pytest.mark.asyncio
async def test_update_current_user(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test updating current user.

    Verifies that a user can update their own profile information.
    """
    # Create test user
    user = await create_test_user(db_session)

    # Get auth headers
    headers = await get_auth_headers(async_client, user.email)

    # Update user
    update_data = {"full_name": "Updated Name", "email": "updated@example.com"}

    response = await async_client.put("/api/v1/users/me", json=update_data, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert (
        data["full_name"] == update_data["full_name"]
    ), f"Expected full_name {update_data['full_name']}, got {data['full_name']}"


@pytest.mark.asyncio
async def test_list_users(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test listing users.

    Verifies that users can be listed with proper pagination.
    """
    # Create test users
    await create_test_user(db_session, "user1@example.com")
    await create_test_user(db_session, "user2@example.com")

    # Get auth headers
    headers = await get_auth_headers(async_client, "user1@example.com")

    # List users
    response = await async_client.get("/api/v1/users/", headers=headers, params={"skip": 0, "limit": 100})
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) >= 2, f"Expected at least 2 users, got {len(data['items'])}"


@pytest.mark.asyncio
async def test_get_user_by_id(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test getting user by ID.

    Verifies that a user can be retrieved by their ID.
    """
    # Create test users
    user1 = await create_test_user(db_session, "user1@example.com")
    user2 = await create_test_user(db_session, "user2@example.com")

    # Get auth headers
    headers = await get_auth_headers(async_client, user1.email)

    # Get user by ID
    response = await async_client.get(f"/api/v1/users/{user2.id}", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "user2@example.com", f"Expected email user2@example.com, got {data['email']}"
    assert data["id"] == user2.id


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Test unauthorized access to protected endpoints.

    Verifies that unauthenticated requests to protected endpoints
    return proper 401 Unauthorized responses.
    """
    response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401, f"Expected status code 401, got {response.status_code}"
