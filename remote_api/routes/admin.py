"""Admin-only routes for user and permission management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import crud as auth_crud
from ..auth.dependencies import require_admin
from ..auth.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    SetUserAccessRequest,
    UpdateUserRequest,
    UserProfile,
)
from ..auth.security import generate_temporary_password
from .. import models

router = APIRouter(prefix="/admin", tags=["admin"])


def _profile(user: models.User, db: Session) -> UserProfile:
    permissions = auth_crud.get_user_permissions(db, user.id)
    automation_ids = auth_crud.get_user_automation_ids(db, user.id)
    client_ids = auth_crud.get_user_client_ids(db, user.id)
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        permissions=permissions,
        automation_ids=automation_ids,
        client_ids=client_ids,
        created_at=user.created_at,
    )


@router.get("/users", response_model=list[UserProfile])
def list_users(
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = auth_crud.list_users(db)
    return [_profile(u, db) for u in users]


@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateUserRequest,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if auth_crud.get_user_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")
    temp_password = generate_temporary_password()
    user = auth_crud.create_user(db, body.email, temp_password, body.full_name, body.role)
    db.commit()
    db.refresh(user)
    profile = _profile(user, db)
    return CreateUserResponse(**profile.model_dump(), temporary_password=temp_password)


@router.get("/users/{user_id}", response_model=UserProfile)
def get_user(
    user_id: UUID,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = auth_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return _profile(user, db)


@router.patch("/users/{user_id}", response_model=UserProfile)
def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = auth_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    auth_crud.update_user(
        db, user,
        full_name=body.full_name,
        is_active=body.is_active,
        role=body.role,
    )
    db.commit()
    db.refresh(user)
    return _profile(user, db)


@router.put("/users/{user_id}/access", response_model=UserProfile)
def set_user_access(
    user_id: UUID,
    body: SetUserAccessRequest,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Replace all permissions and host access for a user in one call."""
    user = auth_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins têm acesso total — não é necessário definir permissões",
        )
    auth_crud.set_user_permissions(db, user_id, body.permissions)
    auth_crud.set_user_automation_access(db, user_id, body.automation_ids)
    auth_crud.set_user_client_access(db, user_id, body.client_ids)
    db.commit()
    db.refresh(user)
    return _profile(user, db)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: UUID,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate a new temporary password and revoke all active sessions."""
    user = auth_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    temp_password = generate_temporary_password()
    auth_crud.update_user(db, user, password=temp_password)
    auth_crud.revoke_all_user_sessions(db, user_id)
    db.commit()
    return {"temporary_password": temp_password}


@router.delete("/users/{user_id}/sessions", status_code=status.HTTP_204_NO_CONTENT)
def revoke_sessions(
    user_id: UUID,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Force-logout: revoke all active sessions for a user."""
    user = auth_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    auth_crud.revoke_all_user_sessions(db, user_id)
    db.commit()
