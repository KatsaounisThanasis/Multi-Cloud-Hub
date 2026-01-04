"""
User Authentication and RBAC System

Implements JWT-based authentication with role-based access control.
Supports three roles: admin, user, viewer
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Header
from pydantic import BaseModel, EmailStr, validator

# JWT Configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print("⚠️  WARNING: JWT_SECRET_KEY not set. Using random key (sessions won't persist across restarts)")

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# User Roles
class UserRole:
    ADMIN = 'admin'
    USER = 'user'
    VIEWER = 'viewer'

    @classmethod
    def all_roles(cls) -> List[str]:
        return [cls.ADMIN, cls.USER, cls.VIEWER]

# Role Permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: ['read', 'write', 'delete', 'manage_users'],
    UserRole.USER: ['read', 'write'],
    UserRole.VIEWER: ['read']
}

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    role: str = UserRole.USER

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

    @validator('role')
    def validate_role(cls, v):
        if v not in UserRole.all_roles():
            raise ValueError(f'Role must be one of: {", ".join(UserRole.all_roles())}')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    permissions: List[str] = []
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if v and len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

# In-memory user storage (in production, use a real database)
users_db: Dict[str, Dict[str, Any]] = {}
user_id_counter = 1

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_user(user_data: UserCreate) -> UserResponse:
    """Create a new user."""
    global user_id_counter

    # Check if user already exists
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user_id = user_id_counter
    user_id_counter += 1

    hashed_pwd = hash_password(user_data.password)

    user = {
        'id': user_id,
        'email': user_data.email,
        'username': user_data.username,
        'password_hash': hashed_pwd,
        'role': user_data.role,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    users_db[user_data.email] = user

    return UserResponse(
        id=user['id'],
        email=user['email'],
        username=user['username'],
        role=user['role'],
        created_at=user['created_at']
    )

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    return users_db.get(email)

def get_all_users() -> List[UserResponse]:
    """Get all users (admin only)."""
    return [
        UserResponse(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            role=user['role'],
            created_at=user['created_at']
        )
        for user in users_db.values()
    ]

def update_user(email: str, update_data: UserUpdate) -> UserResponse:
    """Update user information."""
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if update_data.username:
        user['username'] = update_data.username

    if update_data.password:
        user['password_hash'] = hash_password(update_data.password)

    if update_data.role and update_data.role in UserRole.all_roles():
        user['role'] = update_data.role

    user['updated_at'] = datetime.utcnow()

    return UserResponse(
        id=user['id'],
        email=user['email'],
        username=user['username'],
        role=user['role'],
        created_at=user['created_at']
    )

def delete_user(email: str) -> bool:
    """Delete a user."""
    if email in users_db:
        del users_db[email]
        return True
    return False

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user by email and password."""
    user = users_db.get(email)
    if not user:
        return None

    if not verify_password(password, user['password_hash']):
        return None

    return user

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Get current user from JWT token in Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please provide Authorization header with Bearer token."
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme. Use 'Bearer <token>'")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    payload = decode_access_token(token)
    email = payload.get('sub')

    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def has_permission(user: Dict[str, Any], permission: str) -> bool:
    """Check if a user has a specific permission."""
    role = user.get('role')
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions

# Initialize default users for testing (DEVELOPMENT ONLY)
def initialize_default_users():
    """Create default users for testing and development.

    WARNING: This function only runs in development mode (ENVIRONMENT != 'production').
    In production, users should be created through proper registration or admin tools.
    """
    global user_id_counter

    # Only create default users in development mode
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    if environment == 'production':
        print("ℹ️  Production mode: Skipping default user creation")
        return

    if len(users_db) == 0:
        import secrets

        print("\n🔐 Initializing default users (development mode only)...")
        print("⚠️  WARNING: Default users are for development only. Do not use in production.")

        # Generate random passwords for default users
        admin_pwd = secrets.token_urlsafe(16)
        user_pwd = secrets.token_urlsafe(16)
        viewer_pwd = secrets.token_urlsafe(16)

        # Create admin user
        try:
            admin_user = UserCreate(
                email="admin@example.com",
                password=admin_pwd,
                username="Administrator",
                role=UserRole.ADMIN
            )
            create_user(admin_user)
            print(f"  ✓ Admin user created: admin@example.com / {admin_pwd}")
        except Exception as e:
            print(f"  ✗ Failed to create admin user: {e}")

        # Create regular user
        try:
            regular_user = UserCreate(
                email="user@example.com",
                password=user_pwd,
                username="Regular User",
                role=UserRole.USER
            )
            create_user(regular_user)
            print(f"  ✓ Regular user created: user@example.com / {user_pwd}")
        except Exception as e:
            print(f"  ✗ Failed to create regular user: {e}")

        # Create viewer user
        try:
            viewer_user = UserCreate(
                email="viewer@example.com",
                password=viewer_pwd,
                username="Viewer User",
                role=UserRole.VIEWER
            )
            create_user(viewer_user)
            print(f"  ✓ Viewer user created: viewer@example.com / {viewer_pwd}")
        except Exception as e:
            print(f"  ✗ Failed to create viewer user: {e}")

        print(f"\n📊 Total users: {len(users_db)}")
        print("📝 Note: Save these credentials - they are randomly generated each startup.\n")
