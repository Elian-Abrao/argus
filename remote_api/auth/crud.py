"""Database operations for users, permissions and sessions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from .. import models
from .security import hash_password, hash_token, generate_refresh_token


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter_by(email=email.lower()).first()


def get_user_by_id(db: Session, user_id: UUID) -> models.User | None:
    return db.get(models.User, user_id)


def list_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.created_at).all()


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    role: str = "user",
) -> models.User:
    user = models.User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def update_user(
    db: Session,
    user: models.User,
    full_name: str | None = None,
    is_active: bool | None = None,
    role: str | None = None,
    password: str | None = None,
) -> models.User:
    if full_name is not None:
        user.full_name = full_name
    if is_active is not None:
        user.is_active = is_active
    if role is not None:
        user.role = role
    if password is not None:
        user.password_hash = hash_password(password)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

def get_user_permissions(db: Session, user_id: UUID) -> list[str]:
    rows = db.query(models.UserPermission).filter_by(user_id=user_id).all()
    return [r.permission for r in rows]


def set_user_permissions(db: Session, user_id: UUID, permissions: list[str]) -> None:
    """Replace all permissions for a user."""
    db.query(models.UserPermission).filter_by(user_id=user_id).delete()
    for perm in set(permissions):
        db.add(models.UserPermission(user_id=user_id, permission=perm))
    db.flush()


# ---------------------------------------------------------------------------
# Host access
# ---------------------------------------------------------------------------

def get_user_host_ids(db: Session, user_id: UUID) -> list[UUID]:
    rows = db.query(models.UserHostAccess).filter_by(user_id=user_id).all()
    return [r.host_id for r in rows]


def set_user_host_access(db: Session, user_id: UUID, host_ids: list[UUID]) -> None:
    """Replace all host access entries for a user."""
    db.query(models.UserHostAccess).filter_by(user_id=user_id).delete()
    for host_id in set(host_ids):
        db.add(models.UserHostAccess(user_id=user_id, host_id=host_id))
    db.flush()


# ---------------------------------------------------------------------------
# Automation access
# ---------------------------------------------------------------------------

def get_user_automation_ids(db: Session, user_id: UUID) -> list[UUID]:
    rows = db.query(models.UserAutomationAccess).filter_by(user_id=user_id).all()
    return [r.automation_id for r in rows]


def set_user_automation_access(db: Session, user_id: UUID, automation_ids: list[UUID]) -> None:
    """Replace all automation access entries for a user."""
    db.query(models.UserAutomationAccess).filter_by(user_id=user_id).delete()
    for automation_id in set(automation_ids):
        db.add(models.UserAutomationAccess(user_id=user_id, automation_id=automation_id))
    db.flush()


# ---------------------------------------------------------------------------
# Client access
# ---------------------------------------------------------------------------

def get_user_client_ids(db: Session, user_id: UUID) -> list[UUID]:
    rows = db.query(models.UserClientAccess).filter_by(user_id=user_id).all()
    return [r.client_id for r in rows]


def set_user_client_access(db: Session, user_id: UUID, client_ids: list[UUID]) -> None:
    """Replace all client access entries for a user."""
    db.query(models.UserClientAccess).filter_by(user_id=user_id).delete()
    for client_id in set(client_ids):
        db.add(models.UserClientAccess(user_id=user_id, client_id=client_id))
    db.flush()


# ---------------------------------------------------------------------------
# AI assistant: instance-level access scope
# ---------------------------------------------------------------------------

def get_user_accessible_instance_ids(db: Session, user_id: UUID) -> list[UUID]:
    """Return all automation_instance IDs visible to this user.

    Combines:
    - direct automation access  → instances whose automation_id is in user_automation_access
    - client access             → instances whose client_id is in user_client_access
    """
    from sqlalchemy import or_

    automation_ids = [r.automation_id for r in db.query(models.UserAutomationAccess).filter_by(user_id=user_id).all()]
    client_ids = [r.client_id for r in db.query(models.UserClientAccess).filter_by(user_id=user_id).all()]

    if not automation_ids and not client_ids:
        return []

    conditions = []
    if automation_ids:
        conditions.append(models.AutomationInstance.automation_id.in_(automation_ids))
    if client_ids:
        conditions.append(models.AutomationInstance.client_id.in_(client_ids))

    rows = db.query(models.AutomationInstance.id).filter(or_(*conditions)).distinct().all()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Sessions (refresh tokens)
# ---------------------------------------------------------------------------

def create_session(db: Session, user_id: UUID, expire_days: int = 7) -> str:
    """Create a new session, return the raw refresh token (store only the hash)."""
    raw_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expire_days)
    session = models.UserSession(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    return raw_token


def get_active_session(db: Session, raw_token: str) -> models.UserSession | None:
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    return (
        db.query(models.UserSession)
        .filter(
            models.UserSession.token_hash == token_hash,
            models.UserSession.expires_at > now,
            models.UserSession.revoked_at.is_(None),
        )
        .first()
    )


def revoke_session(db: Session, session: models.UserSession) -> None:
    session.revoked_at = datetime.now(timezone.utc)
    db.flush()


def revoke_all_user_sessions(db: Session, user_id: UUID) -> int:
    now = datetime.now(timezone.utc)
    count = (
        db.query(models.UserSession)
        .filter(
            models.UserSession.user_id == user_id,
            models.UserSession.revoked_at.is_(None),
        )
        .update({"revoked_at": now})
    )
    db.flush()
    return count
