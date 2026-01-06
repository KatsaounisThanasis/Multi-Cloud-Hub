"""
Unit tests for core/auth.py module
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import jwt
import os

from backend.core.auth import (
    UserRole, UserCreate, UserLogin, UserUpdate, UserResponse,
    create_user, authenticate_user, get_current_user, create_access_token,
    get_all_users, update_user, delete_user, has_permission,
    ROLE_PERMISSIONS, SECRET_KEY, ALGORITHM
)


class TestUserRole:
    """Tests for UserRole class."""

    def test_role_values(self):
        """Test role constant values."""
        assert UserRole.ADMIN == 'admin'
        assert UserRole.USER == 'user'
        assert UserRole.VIEWER == 'viewer'

    def test_all_roles(self):
        """Test all_roles method."""
        roles = UserRole.all_roles()
        assert 'admin' in roles
        assert 'user' in roles
        assert 'viewer' in roles
        assert len(roles) == 3


class TestUserModels:
    """Tests for Pydantic user models."""

    def test_user_create_valid(self):
        """Test creating valid UserCreate."""
        user = UserCreate(
            email="test@example.com",
            password="password123",
            username="testuser"
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER  # default

    def test_user_create_with_role(self):
        """Test creating UserCreate with role."""
        user = UserCreate(
            email="admin@example.com",
            password="adminpass",
            username="admin",
            role=UserRole.ADMIN
        )
        assert user.role == UserRole.ADMIN

    def test_user_create_invalid_role(self):
        """Test UserCreate with invalid role."""
        with pytest.raises(ValueError):
            UserCreate(
                email="test@example.com",
                password="password123",
                username="testuser",
                role="superuser"  # Invalid
            )

    def test_user_create_short_password(self):
        """Test UserCreate with short password."""
        with pytest.raises(ValueError):
            UserCreate(
                email="test@example.com",
                password="123",  # Too short
                username="testuser"
            )

    def test_user_login_valid(self):
        """Test creating valid UserLogin."""
        login = UserLogin(
            email="test@example.com",
            password="password123"
        )
        assert login.email == "test@example.com"

    def test_user_update_partial(self):
        """Test UserUpdate with partial data."""
        update = UserUpdate(username="newname")
        assert update.username == "newname"
        assert update.role is None


class TestTokenFunctions:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "test@example.com"
        assert "exp" in decoded

    def test_create_access_token_with_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "test@example.com"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "test@example.com"


class TestUserCRUD:
    """Tests for user CRUD operations."""

    def test_create_user(self):
        """Test creating a new user."""
        # Clear users_db for test isolation
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        user_data = UserCreate(
            email="newuser@example.com",
            password="password123",
            username="newuser"
        )
        user = create_user(user_data)

        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.role == UserRole.USER

    def test_create_duplicate_user(self):
        """Test creating user with duplicate email."""
        from fastapi import HTTPException
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        user_data = UserCreate(
            email="duplicate@example.com",
            password="password123",
            username="user1"
        )
        create_user(user_data)

        # Try to create again with same email
        user_data2 = UserCreate(
            email="duplicate@example.com",
            password="password456",
            username="user2"
        )
        with pytest.raises(HTTPException) as exc_info:
            create_user(user_data2)

        assert exc_info.value.status_code == 400

    def test_authenticate_user_success(self):
        """Test successful authentication."""
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        user_data = UserCreate(
            email="auth@example.com",
            password="mypassword",
            username="authuser"
        )
        create_user(user_data)

        result = authenticate_user("auth@example.com", "mypassword")
        assert result is not None
        assert result['email'] == "auth@example.com"

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        user_data = UserCreate(
            email="auth2@example.com",
            password="correctpassword",
            username="authuser2"
        )
        create_user(user_data)

        result = authenticate_user("auth2@example.com", "wrongpassword")
        assert result is None

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        result = authenticate_user("nonexistent@example.com", "anypassword")
        assert result is None

    def test_get_all_users(self):
        """Test getting all users."""
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        # Create some users
        for i in range(3):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                password="password123",
                username=f"user{i}"
            )
            create_user(user_data)

        users = get_all_users()
        assert len(users) == 3

    def test_update_user(self):
        """Test updating a user."""
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        user_data = UserCreate(
            email="update@example.com",
            password="password123",
            username="oldname"
        )
        create_user(user_data)

        update_data = UserUpdate(username="newname")
        updated = update_user("update@example.com", update_data)

        assert updated.username == "newname"

    def test_update_user_not_found(self):
        """Test updating non-existent user."""
        from fastapi import HTTPException

        update_data = UserUpdate(username="newname")
        with pytest.raises(HTTPException) as exc_info:
            update_user("nonexistent@example.com", update_data)

        assert exc_info.value.status_code == 404

    def test_delete_user(self):
        """Test deleting a user."""
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        user_data = UserCreate(
            email="delete@example.com",
            password="password123",
            username="deleteuser"
        )
        create_user(user_data)

        result = delete_user("delete@example.com")
        assert result is True

        # Verify deletion
        users = get_all_users()
        emails = [u.email for u in users]
        assert "delete@example.com" not in emails

    def test_delete_user_not_found(self):
        """Test deleting non-existent user."""
        result = delete_user("nonexistent@example.com")
        assert result is False


class TestPermissions:
    """Tests for permission checks."""

    def test_admin_has_manage_users(self):
        """Test admin has manage_users permission."""
        admin_user = {'role': UserRole.ADMIN}
        assert has_permission(admin_user, 'manage_users') is True

    def test_user_no_manage_users(self):
        """Test regular user doesn't have manage_users."""
        regular_user = {'role': UserRole.USER}
        assert has_permission(regular_user, 'manage_users') is False

    def test_viewer_has_read(self):
        """Test viewer has read permission."""
        viewer = {'role': UserRole.VIEWER}
        assert has_permission(viewer, 'read') is True

    def test_viewer_no_write(self):
        """Test viewer doesn't have write permission."""
        viewer = {'role': UserRole.VIEWER}
        assert has_permission(viewer, 'write') is False

    def test_role_permissions_structure(self):
        """Test ROLE_PERMISSIONS has correct structure."""
        assert UserRole.ADMIN in ROLE_PERMISSIONS
        assert UserRole.USER in ROLE_PERMISSIONS
        assert UserRole.VIEWER in ROLE_PERMISSIONS

        assert 'manage_users' in ROLE_PERMISSIONS[UserRole.ADMIN]
        assert 'read' in ROLE_PERMISSIONS[UserRole.USER]
        assert 'write' in ROLE_PERMISSIONS[UserRole.USER]


class TestGetCurrentUser:
    """Tests for get_current_user function."""

    def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        from backend.core import auth
        auth.users_db.clear()
        auth.user_id_counter = 0

        # Create user
        user_data = UserCreate(
            email="current@example.com",
            password="password123",
            username="currentuser"
        )
        create_user(user_data)

        # Create token
        token = create_access_token({"sub": "current@example.com"})

        # Get current user
        user = get_current_user(authorization=f"Bearer {token}")
        assert user['email'] == "current@example.com"

    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization="Bearer invalid_token")

        assert exc_info.value.status_code == 401

    def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=None)

        assert exc_info.value.status_code == 401

    def test_get_current_user_expired_token(self):
        """Test getting current user with expired token."""
        from fastapi import HTTPException

        # Create expired token
        expired_token = jwt.encode(
            {"sub": "test@example.com", "exp": datetime.utcnow() - timedelta(hours=1)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=f"Bearer {expired_token}")

        assert exc_info.value.status_code == 401
