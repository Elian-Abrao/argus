"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Permissions
PERM_VIEW_ALL = "view_all"
PERM_RUN_AUTOMATIONS = "run_automations"
PERM_CONFIGURE_ARGS = "configure_args"


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_error

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_error

    user = db.get(models.User, UUID(user_id))
    if not user or not user.is_active:
        raise credentials_error

    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return user


def require_permission(permission: str):
    """Return a dependency that requires the user to have a specific permission (or be admin)."""
    def _check(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> models.User:
        if user.role == "admin":
            return user
        has = db.query(models.UserPermission).filter_by(user_id=user.id, permission=permission).first()
        if not has:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permissão necessária: {permission}")
        return user
    return _check


def get_accessible_host_ids(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UUID] | None:
    """Return None if the user can see all hosts, or a list of allowed host UUIDs.

    Admins and users with ``view_all`` get None (unrestricted).
    Other users get the list from ``user_host_access``.
    """
    if user.role == "admin":
        return None
    has_view_all = db.query(models.UserPermission).filter_by(
        user_id=user.id, permission=PERM_VIEW_ALL
    ).first()
    if has_view_all:
        return None
    rows = db.query(models.UserHostAccess).filter_by(user_id=user.id).all()
    return [r.host_id for r in rows]


def get_accessible_automation_ids(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UUID] | None:
    """Return None if the user can see all automations, or a list of allowed automation UUIDs.

    Admins and users with ``view_all`` get None (unrestricted).
    Other users get the union of:
    - direct automation access (``user_automation_access``)
    - automations linked to allowed clients (``user_client_access`` → ``automation_instances``)
    """
    if user.role == "admin":
        return None
    has_view_all = db.query(models.UserPermission).filter_by(
        user_id=user.id, permission=PERM_VIEW_ALL
    ).first()
    if has_view_all:
        return None

    # Direct automation access
    direct_rows = db.query(models.UserAutomationAccess).filter_by(user_id=user.id).all()
    automation_ids = {r.automation_id for r in direct_rows}

    # Automation access via client
    client_rows = db.query(models.UserClientAccess).filter_by(user_id=user.id).all()
    if client_rows:
        client_ids = [r.client_id for r in client_rows]
        from sqlalchemy import select, distinct
        stmt = (
            select(distinct(models.AutomationInstance.automation_id))
            .where(models.AutomationInstance.client_id.in_(client_ids))
        )
        for (aid,) in db.execute(stmt).all():
            automation_ids.add(aid)

    return list(automation_ids)
