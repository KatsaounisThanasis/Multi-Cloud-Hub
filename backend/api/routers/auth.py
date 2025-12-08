"""
Authentication Router

Handles user authentication, registration, and user management.
"""

from fastapi import APIRouter, HTTPException, Depends, status
import logging

from backend.api.schemas import StandardResponse, success_response
from backend.core.auth import (
    UserCreate, UserLogin, UserUpdate,
    create_user, authenticate_user, get_current_user,
    create_access_token, get_all_users, update_user, delete_user,
    has_permission, ROLE_PERMISSIONS
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register",
    summary="Register New User",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user account."""
    try:
        user = create_user(user_data)
        return success_response(
            message=f"User '{user.username}' registered successfully",
            data={"user": user.dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login",
    summary="Login",
    response_model=StandardResponse)
async def login(credentials: UserLogin):
    """Authenticate user and get access token."""
    user = authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": user['email']})
    user_permissions = ROLE_PERMISSIONS.get(user['role'], [])

    return success_response(
        message="Login successful",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "username": user['username'],
                "role": user['role'],
                "permissions": user_permissions
            }
        }
    )


@router.get("/me",
    summary="Get Current User",
    response_model=StandardResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information."""
    permissions = [p for p in ['read', 'write', 'delete', 'manage_users']
                   if has_permission(current_user, p)]

    return success_response(
        message="User information retrieved",
        data={
            "user": {
                "id": current_user['id'],
                "email": current_user['email'],
                "username": current_user['username'],
                "role": current_user['role'],
                "created_at": current_user['created_at'].isoformat()
            },
            "permissions": permissions
        }
    )


@router.get("/users",
    summary="List All Users",
    response_model=StandardResponse,
    tags=["Admin"])
async def list_users(current_user: dict = Depends(get_current_user)):
    """List all registered users. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    users = get_all_users()
    return success_response(
        message=f"Retrieved {len(users)} users",
        data={"users": [u.dict() for u in users], "total": len(users)}
    )


@router.put("/users/{email}",
    summary="Update User",
    response_model=StandardResponse,
    tags=["Admin"])
async def update_user_endpoint(
    email: str,
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user information."""
    is_self = current_user['email'] == email
    is_admin = has_permission(current_user, 'manage_users')

    if not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    if update_data.role and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can change roles")

    try:
        updated_user = update_user(email, update_data)
        return success_response(
            message=f"User '{updated_user.username}' updated",
            data={"user": updated_user.dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{email}",
    summary="Delete User",
    response_model=StandardResponse,
    tags=["Admin"])
async def delete_user_endpoint(
    email: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    if current_user['email'] == email:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    if not delete_user(email):
        raise HTTPException(status_code=404, detail="User not found")

    return success_response(
        message=f"User '{email}' deleted",
        data={"deleted_email": email}
    )
