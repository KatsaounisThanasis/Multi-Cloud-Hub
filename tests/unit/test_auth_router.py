"""
Unit tests for Authentication Router
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from backend.api.routes import app
from backend.core.auth import UserRole, get_current_user


@pytest.fixture
def mock_user():
    """Create mock user data."""
    return {
        'id': 1,
        'email': 'test@example.com',
        'username': 'testuser',
        'role': UserRole.USER,
        'created_at': datetime.now()
    }


@pytest.fixture
def mock_admin_user():
    """Create mock admin user data."""
    return {
        'id': 1,
        'email': 'admin@example.com',
        'username': 'admin',
        'role': UserRole.ADMIN,
        'created_at': datetime.now()
    }


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def authenticated_client(mock_user):
    """Create test client with authenticated user."""
    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    # Add Authorization header to bypass CSRF check for API requests
    client = TestClient(app, headers={"Authorization": "Bearer test-token"})
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(mock_admin_user):
    """Create test client with admin user."""
    def override_get_current_user():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    # Add Authorization header to bypass CSRF check for API requests
    client = TestClient(app, headers={"Authorization": "Bearer test-admin-token"})
    yield client
    app.dependency_overrides.clear()


class TestAuthRegister:
    """Tests for /auth/register endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        with patch('backend.api.routers.auth.create_user') as mock_create:
            mock_user_obj = MagicMock()
            mock_user_obj.username = 'newuser'
            mock_user_obj.dict.return_value = {
                'id': 1,
                'email': 'new@example.com',
                'username': 'newuser',
                'role': 'user'
            }
            mock_create.return_value = mock_user_obj

            response = client.post("/auth/register", json={
                "email": "new@example.com",
                "password": "password123",
                "username": "newuser"
            })

            assert response.status_code == 201
            assert response.json()["success"] is True
            assert "newuser" in response.json()["message"]

    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email."""
        from fastapi import HTTPException
        with patch('backend.api.routers.auth.create_user') as mock_create:
            mock_create.side_effect = HTTPException(status_code=400, detail="Email already registered")

            response = client.post("/auth/register", json={
                "email": "existing@example.com",
                "password": "password123",
                "username": "newuser"
            })

            assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post("/auth/register", json={
            "email": "invalid-email",
            "password": "password123",
            "username": "newuser"
        })

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client):
        """Test registration with short password."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "123",
            "username": "newuser"
        })

        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Tests for /auth/login endpoint."""

    def test_login_success(self, client):
        """Test successful login."""
        with patch('backend.api.routers.auth.authenticate_user') as mock_auth, \
             patch('backend.api.routers.auth.create_access_token') as mock_token:
            mock_auth.return_value = {
                'id': 1,
                'email': 'test@example.com',
                'username': 'testuser',
                'role': 'user'
            }
            mock_token.return_value = "test_token_123"

            response = client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })

            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["data"]["access_token"] == "test_token_123"
            assert response.json()["data"]["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch('backend.api.routers.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = None

            response = client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })

            assert response.status_code == 401
            assert "Invalid" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post("/auth/login", json={
            "email": "test@example.com"
        })

        assert response.status_code == 422


class TestAuthMe:
    """Tests for /auth/me endpoint."""

    def test_get_me_authenticated(self, authenticated_client, mock_user):
        """Test getting current user info when authenticated."""
        response = authenticated_client.get("/auth/me")

        assert response.status_code == 200
        assert response.json()["data"]["user"]["email"] == mock_user['email']

    def test_get_me_unauthenticated(self, client):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestUserManagement:
    """Tests for user management endpoints."""

    def test_list_users_as_admin(self, admin_client):
        """Test listing users as admin."""
        with patch('backend.api.routers.auth.get_all_users') as mock_get_all:
            mock_user_obj = MagicMock()
            mock_user_obj.dict.return_value = {'id': 1, 'email': 'user@example.com'}
            mock_get_all.return_value = [mock_user_obj]

            response = admin_client.get("/auth/users")

            assert response.status_code == 200
            assert response.json()["data"]["total"] == 1

    def test_list_users_as_non_admin(self, authenticated_client):
        """Test listing users as non-admin (should fail)."""
        response = authenticated_client.get("/auth/users")
        assert response.status_code == 403

    def test_update_user_self(self, authenticated_client, mock_user):
        """Test updating own user info."""
        with patch('backend.api.routers.auth.update_user') as mock_update:
            mock_updated = MagicMock()
            mock_updated.username = 'updateduser'
            mock_updated.dict.return_value = {'username': 'updateduser'}
            mock_update.return_value = mock_updated

            response = authenticated_client.put(
                f"/auth/users/{mock_user['email']}",
                json={"username": "updateduser"}
            )

            assert response.status_code == 200

    def test_update_user_other_as_non_admin(self, authenticated_client):
        """Test updating another user as non-admin (should fail)."""
        response = authenticated_client.put(
            "/auth/users/other@example.com",
            json={"username": "hacker"}
        )
        assert response.status_code == 403

    def test_update_role_as_non_admin(self, authenticated_client, mock_user):
        """Test changing role as non-admin (should fail)."""
        response = authenticated_client.put(
            f"/auth/users/{mock_user['email']}",
            json={"role": "admin"}
        )
        assert response.status_code == 403

    def test_delete_user_as_admin(self, admin_client):
        """Test deleting user as admin."""
        with patch('backend.api.routers.auth.delete_user') as mock_delete:
            mock_delete.return_value = True

            response = admin_client.delete("/auth/users/user@example.com")

            assert response.status_code == 200
            assert "deleted" in response.json()["message"].lower()

    def test_delete_user_not_found(self, admin_client):
        """Test deleting non-existent user."""
        with patch('backend.api.routers.auth.delete_user') as mock_delete:
            mock_delete.return_value = False

            response = admin_client.delete("/auth/users/nonexistent@example.com")

            assert response.status_code == 404

    def test_delete_self_as_admin(self, admin_client, mock_admin_user):
        """Test admin cannot delete self."""
        response = admin_client.delete(f"/auth/users/{mock_admin_user['email']}")

        assert response.status_code == 400
        assert "own account" in response.json()["detail"]

    def test_delete_user_as_non_admin(self, authenticated_client):
        """Test deleting user as non-admin (should fail)."""
        response = authenticated_client.delete("/auth/users/other@example.com")
        assert response.status_code == 403
