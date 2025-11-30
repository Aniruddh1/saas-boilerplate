"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data  # Should not expose password


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test registration with existing email fails."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": test_user.email,
            "password": "anotherpassword",
            "name": "Another User",
        },
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test registration with weak password fails."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "123",  # Too short
            "name": "Test",
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, user_factory):
    """Test successful login."""
    # Create user with known password
    password = "testpassword123"
    user = await user_factory.create(
        email="login@example.com",
        password=password,
    )

    response = await client.post(
        "/api/auth/login",
        data={
            "username": user.email,
            "password": password,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password."""
    response = await client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        "/api/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "anypassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, user_factory):
    """Test token refresh."""
    # Login first to get refresh token
    password = "testpassword123"
    user = await user_factory.create(password=password)

    login_response = await client.post(
        "/api/auth/login",
        data={
            "username": user.email,
            "password": password,
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Use refresh token
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await client.get("/api/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(
    client: AsyncClient,
    test_user,
    auth_headers,
):
    """Test accessing protected endpoint with valid token."""
    response = await client.get("/api/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Test accessing endpoint with invalid token."""
    response = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
