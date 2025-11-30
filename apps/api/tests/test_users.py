"""
Tests for user endpoints.
"""

import pytest
from httpx import AsyncClient

from src.models.user import User


@pytest.mark.asyncio
async def test_get_current_user(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
):
    """Test getting current user profile."""
    response = await client.get("/api/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name


@pytest.mark.asyncio
async def test_update_current_user(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict,
):
    """Test updating current user profile."""
    response = await client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["email"] == test_user.email  # Email unchanged


@pytest.mark.asyncio
async def test_list_users_requires_admin(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test that listing users requires admin."""
    response = await client.get("/api/users", headers=auth_headers)

    # Regular user should not have access
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_as_admin(
    client: AsyncClient,
    admin_auth_headers: dict,
    user_factory,
):
    """Test listing users as admin."""
    # Create some test users
    await user_factory.create(email="user1@example.com")
    await user_factory.create(email="user2@example.com")

    response = await client.get("/api/users", headers=admin_auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_users_pagination(
    client: AsyncClient,
    admin_auth_headers: dict,
    user_factory,
):
    """Test user list pagination."""
    # Create multiple users
    for i in range(5):
        await user_factory.create(email=f"paginated{i}@example.com")

    # Get first page
    response = await client.get(
        "/api/users?page=1&per_page=2",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2


@pytest.mark.asyncio
async def test_list_users_search(
    client: AsyncClient,
    admin_auth_headers: dict,
    user_factory,
):
    """Test user search."""
    await user_factory.create(email="searchable@example.com", name="Searchable User")
    await user_factory.create(email="other@example.com", name="Other User")

    response = await client.get(
        "/api/users?search=searchable",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Should find user by email or name
    assert any("searchable" in item["email"].lower() for item in data["items"])


@pytest.mark.asyncio
async def test_get_user_by_id(
    client: AsyncClient,
    admin_auth_headers: dict,
    test_user: User,
):
    """Test getting user by ID as admin."""
    response = await client.get(
        f"/api/users/{test_user.id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_get_user_not_found(
    client: AsyncClient,
    admin_auth_headers: dict,
):
    """Test getting non-existent user."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/users/{fake_id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_as_admin(
    client: AsyncClient,
    admin_auth_headers: dict,
    user_factory,
):
    """Test deleting user as admin."""
    user_to_delete = await user_factory.create(email="todelete@example.com")

    response = await client.delete(
        f"/api/users/{user_to_delete.id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 204

    # Verify deleted
    get_response = await client.get(
        f"/api/users/{user_to_delete.id}",
        headers=admin_auth_headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_forbidden_for_regular_user(
    client: AsyncClient,
    auth_headers: dict,
    user_factory,
):
    """Test that regular users cannot delete users."""
    user_to_delete = await user_factory.create()

    response = await client.delete(
        f"/api/users/{user_to_delete.id}",
        headers=auth_headers,
    )

    assert response.status_code == 403
