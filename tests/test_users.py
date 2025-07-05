"""
User management tests
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.sqlalchemy.models.user import UserModel
from src.utils.security_utils import hash_password


async def create_test_user(db_session: AsyncSession, email: str = "test@example.com") -> UserModel:
    """Helper function to create a test user"""
    user = UserModel(email=email, hashed_password=hash_password("password123"), full_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def get_auth_headers(client: AsyncClient, email: str = "test@example.com") -> dict:
    """Helper function to get authentication headers"""
    login_data = {"username": email, "password": "password123"}

    response = await client.post("/api/v1/auth/login", data=login_data)
    tokens = response.json()

    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, db_session: AsyncSession):
    """Test getting current user info"""
    # Create test user
    user = await create_test_user(db_session)

    # Get auth headers
    headers = await get_auth_headers(client, user.email)

    # Get current user
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == user.email
    assert data["full_name"] == user.full_name


@pytest.mark.asyncio
async def test_update_current_user(client: AsyncClient, db_session: AsyncSession):
    """Test updating current user"""
    # Create test user
    user = await create_test_user(db_session)

    # Get auth headers
    headers = await get_auth_headers(client, user.email)

    # Update user
    update_data = {"full_name": "Updated Name"}

    response = await client.put("/api/v1/users/me", json=update_data, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, db_session: AsyncSession):
    """Test listing users"""
    # Create test users
    await create_test_user(db_session, "user1@example.com")
    await create_test_user(db_session, "user2@example.com")

    # Get auth headers
    headers = await get_auth_headers(client, "user1@example.com")

    # List users
    response = await client.get("/api/v1/users/", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, db_session: AsyncSession):
    """Test getting user by ID"""
    # Create test users
    user1 = await create_test_user(db_session, "user1@example.com")
    user2 = await create_test_user(db_session, "user2@example.com")

    # Get auth headers
    headers = await get_auth_headers(client, user1.email)

    # Get user by ID
    response = await client.get(f"/api/v1/users/{user2.id}", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == user2.email
    assert data["id"] == user2.id


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test unauthorized access to protected endpoints"""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
