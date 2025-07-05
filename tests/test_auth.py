"""
Authentication tests
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.sqlalchemy.models.user import UserModel
from src.utils.security_utils import hash_password


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration"""
    user_data = {"email": "test@example.com", "password": "TestPassword123", "full_name": "Test User"}

    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    """Test registration with duplicate email"""
    # Create existing user
    existing_user = UserModel(
        email="existing@example.com", hashed_password=hash_password("password123"), full_name="Existing User"
    )
    db_session.add(existing_user)
    await db_session.commit()

    # Try to register with same email
    user_data = {"email": "existing@example.com", "password": "TestPassword123", "full_name": "New User"}

    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login"""
    # Create test user
    test_user = UserModel(email="login@example.com", hashed_password=hash_password("password123"), full_name="Login User")
    db_session.add(test_user)
    await db_session.commit()

    # Login
    login_data = {"username": "login@example.com", "password": "password123"}

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials"""
    login_data = {"username": "nonexistent@example.com", "password": "wrongpassword"}

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session: AsyncSession):
    """Test token refresh"""
    # Create test user and login
    test_user = UserModel(email="refresh@example.com", hashed_password=hash_password("password123"), full_name="Refresh User")
    db_session.add(test_user)
    await db_session.commit()

    # Login to get tokens
    login_data = {"username": "refresh@example.com", "password": "password123"}

    login_response = await client.post("/api/v1/auth/login", data=login_data)
    tokens = login_response.json()

    # Refresh token
    refresh_data = {"refresh_token": tokens["refresh_token"]}

    response = await client.post("/api/v1/auth/refresh", json=refresh_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
