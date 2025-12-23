"""
Cloud Accounts Router

Handles cloud account management and user permissions for multi-subscription support.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import uuid
from datetime import datetime

from backend.api.schemas import StandardResponse, success_response
from backend.core.auth import get_current_user, has_permission
from backend.core.database import SessionLocal, CloudAccount, UserCloudPermission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cloud-accounts", tags=["Cloud Accounts"])


# ================================================================
# Pydantic Models
# ================================================================

class CloudAccountCreate(BaseModel):
    """Schema for creating a cloud account"""
    name: str = Field(..., min_length=1, max_length=200)
    provider: str = Field(..., pattern="^(azure|gcp)$")
    # Azure fields
    subscription_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    # GCP fields
    project_id: Optional[str] = None
    region: Optional[str] = None


class CloudAccountUpdate(BaseModel):
    """Schema for updating a cloud account"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    subscription_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    project_id: Optional[str] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionCreate(BaseModel):
    """Schema for assigning permissions"""
    user_email: str = Field(..., min_length=1)
    can_deploy: bool = True
    can_view: bool = True


class PermissionUpdate(BaseModel):
    """Schema for updating permissions"""
    can_deploy: Optional[bool] = None
    can_view: Optional[bool] = None


# ================================================================
# Database Session Helper
# ================================================================

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================================================================
# Cloud Account Endpoints
# ================================================================

@router.get("",
    summary="List Cloud Accounts",
    response_model=StandardResponse)
async def list_cloud_accounts(
    current_user: dict = Depends(get_current_user)
):
    """List all cloud accounts. Admins see all, users see only permitted accounts."""
    db = SessionLocal()
    try:
        is_admin = has_permission(current_user, 'manage_users')

        if is_admin:
            # Admins see all accounts
            accounts = db.query(CloudAccount).all()
        else:
            # Regular users see only accounts they have permission for
            permissions = db.query(UserCloudPermission).filter(
                UserCloudPermission.user_email == current_user['email']
            ).all()
            account_ids = [p.cloud_account_id for p in permissions]
            accounts = db.query(CloudAccount).filter(
                CloudAccount.id.in_(account_ids)
            ).all() if account_ids else []

        return success_response(
            message=f"Retrieved {len(accounts)} cloud accounts",
            data={
                "accounts": [acc.to_dict(include_secrets=False) for acc in accounts],
                "total": len(accounts)
            }
        )
    finally:
        db.close()


@router.post("",
    summary="Create Cloud Account",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED)
async def create_cloud_account(
    account_data: CloudAccountCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        # Validate provider-specific fields
        if account_data.provider == 'azure' and not account_data.subscription_id:
            raise HTTPException(status_code=400, detail="subscription_id is required for Azure accounts")
        if account_data.provider == 'gcp' and not account_data.project_id:
            raise HTTPException(status_code=400, detail="project_id is required for GCP accounts")

        account = CloudAccount(
            id=str(uuid.uuid4())[:8],
            name=account_data.name,
            provider=account_data.provider,
            subscription_id=account_data.subscription_id,
            tenant_id=account_data.tenant_id,
            client_id=account_data.client_id,
            client_secret=account_data.client_secret,
            project_id=account_data.project_id,
            region=account_data.region,
            is_active='true',
            created_at=datetime.utcnow(),
            created_by=current_user['email']
        )

        db.add(account)
        db.commit()
        db.refresh(account)

        logger.info(f"Cloud account '{account.name}' created by {current_user['email']}")

        return success_response(
            message=f"Cloud account '{account.name}' created successfully",
            data={"account": account.to_dict(include_secrets=False)}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating cloud account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ================================================================
# User Permission Check Endpoint (MUST be before /{account_id})
# ================================================================

@router.get("/user/permissions",
    summary="Get Current User's Cloud Permissions",
    response_model=StandardResponse)
async def get_user_permissions(
    current_user: dict = Depends(get_current_user)
):
    """Get all cloud account permissions for the current user."""
    db = SessionLocal()
    try:
        is_admin = has_permission(current_user, 'manage_users')

        if is_admin:
            # Admins have full access to all accounts
            accounts = db.query(CloudAccount).filter(CloudAccount.is_active == 'true').all()
            permissions_data = [
                {
                    "account": acc.to_dict(include_secrets=False),
                    "can_deploy": True,
                    "can_view": True
                }
                for acc in accounts
            ]
        else:
            # Get user's specific permissions
            permissions = db.query(UserCloudPermission).filter(
                UserCloudPermission.user_email == current_user['email']
            ).all()

            permissions_data = []
            for perm in permissions:
                account = db.query(CloudAccount).filter(
                    CloudAccount.id == perm.cloud_account_id,
                    CloudAccount.is_active == 'true'
                ).first()
                if account:
                    permissions_data.append({
                        "account": account.to_dict(include_secrets=False),
                        "can_deploy": perm.can_deploy == 'true',
                        "can_view": perm.can_view == 'true'
                    })

        return success_response(
            message=f"Retrieved {len(permissions_data)} account permissions",
            data={
                "permissions": permissions_data,
                "is_admin": is_admin
            }
        )
    finally:
        db.close()


# ================================================================
# Cloud Account CRUD Endpoints
# ================================================================

@router.get("/{account_id}",
    summary="Get Cloud Account",
    response_model=StandardResponse)
async def get_cloud_account(
    account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific cloud account by ID."""
    db = SessionLocal()
    try:
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()

        if not account:
            raise HTTPException(status_code=404, detail="Cloud account not found")

        # Check permissions
        is_admin = has_permission(current_user, 'manage_users')
        if not is_admin:
            permission = db.query(UserCloudPermission).filter(
                UserCloudPermission.user_email == current_user['email'],
                UserCloudPermission.cloud_account_id == account_id
            ).first()
            if not permission:
                raise HTTPException(status_code=403, detail="Access denied to this cloud account")

        return success_response(
            message="Cloud account retrieved",
            data={"account": account.to_dict(include_secrets=is_admin)}
        )
    finally:
        db.close()


@router.put("/{account_id}",
    summary="Update Cloud Account",
    response_model=StandardResponse)
async def update_cloud_account(
    account_id: str,
    update_data: CloudAccountUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()

        if not account:
            raise HTTPException(status_code=404, detail="Cloud account not found")

        # Update fields
        if update_data.name is not None:
            account.name = update_data.name
        if update_data.subscription_id is not None:
            account.subscription_id = update_data.subscription_id
        if update_data.tenant_id is not None:
            account.tenant_id = update_data.tenant_id
        if update_data.client_id is not None:
            account.client_id = update_data.client_id
        if update_data.client_secret is not None:
            account.client_secret = update_data.client_secret
        if update_data.project_id is not None:
            account.project_id = update_data.project_id
        if update_data.region is not None:
            account.region = update_data.region
        if update_data.is_active is not None:
            account.is_active = 'true' if update_data.is_active else 'false'

        db.commit()
        db.refresh(account)

        logger.info(f"Cloud account '{account.name}' updated by {current_user['email']}")

        return success_response(
            message=f"Cloud account '{account.name}' updated successfully",
            data={"account": account.to_dict(include_secrets=False)}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating cloud account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{account_id}",
    summary="Delete Cloud Account",
    response_model=StandardResponse)
async def delete_cloud_account(
    account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()

        if not account:
            raise HTTPException(status_code=404, detail="Cloud account not found")

        account_name = account.name

        # Delete associated permissions first
        db.query(UserCloudPermission).filter(
            UserCloudPermission.cloud_account_id == account_id
        ).delete()

        db.delete(account)
        db.commit()

        logger.info(f"Cloud account '{account_name}' deleted by {current_user['email']}")

        return success_response(
            message=f"Cloud account '{account_name}' deleted successfully",
            data={"deleted_id": account_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting cloud account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ================================================================
# Permission Endpoints
# ================================================================

@router.get("/{account_id}/permissions",
    summary="List Account Permissions",
    response_model=StandardResponse)
async def list_account_permissions(
    account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all user permissions for a cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        # Verify account exists
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Cloud account not found")

        permissions = db.query(UserCloudPermission).filter(
            UserCloudPermission.cloud_account_id == account_id
        ).all()

        return success_response(
            message=f"Retrieved {len(permissions)} permissions",
            data={
                "permissions": [p.to_dict() for p in permissions],
                "total": len(permissions)
            }
        )
    finally:
        db.close()


@router.post("/{account_id}/permissions",
    summary="Assign Permission",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED)
async def assign_permission(
    account_id: str,
    permission_data: PermissionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Assign a user permission to a cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        # Verify account exists
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Cloud account not found")

        # Check if permission already exists
        existing = db.query(UserCloudPermission).filter(
            UserCloudPermission.user_email == permission_data.user_email,
            UserCloudPermission.cloud_account_id == account_id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Permission already exists for this user")

        permission = UserCloudPermission(
            id=str(uuid.uuid4())[:8],
            user_email=permission_data.user_email,
            cloud_account_id=account_id,
            can_deploy='true' if permission_data.can_deploy else 'false',
            can_view='true' if permission_data.can_view else 'false',
            created_at=datetime.utcnow()
        )

        db.add(permission)
        db.commit()
        db.refresh(permission)

        logger.info(f"Permission assigned to {permission_data.user_email} for account '{account.name}'")

        return success_response(
            message=f"Permission assigned to {permission_data.user_email}",
            data={"permission": permission.to_dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error assigning permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{account_id}/permissions/{user_email}",
    summary="Update Permission",
    response_model=StandardResponse)
async def update_permission(
    account_id: str,
    user_email: str,
    update_data: PermissionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a user's permission for a cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        permission = db.query(UserCloudPermission).filter(
            UserCloudPermission.user_email == user_email,
            UserCloudPermission.cloud_account_id == account_id
        ).first()

        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        if update_data.can_deploy is not None:
            permission.can_deploy = 'true' if update_data.can_deploy else 'false'
        if update_data.can_view is not None:
            permission.can_view = 'true' if update_data.can_view else 'false'

        db.commit()
        db.refresh(permission)

        return success_response(
            message=f"Permission updated for {user_email}",
            data={"permission": permission.to_dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{account_id}/permissions/{user_email}",
    summary="Remove Permission",
    response_model=StandardResponse)
async def remove_permission(
    account_id: str,
    user_email: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a user's permission for a cloud account. Admin only."""
    if not has_permission(current_user, 'manage_users'):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db = SessionLocal()
    try:
        permission = db.query(UserCloudPermission).filter(
            UserCloudPermission.user_email == user_email,
            UserCloudPermission.cloud_account_id == account_id
        ).first()

        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        db.delete(permission)
        db.commit()

        logger.info(f"Permission removed for {user_email} from account {account_id}")

        return success_response(
            message=f"Permission removed for {user_email}",
            data={"removed_email": user_email}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
