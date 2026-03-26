"""Authentication routes: login, logout, refresh token, current user."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import crud as auth_crud
from ..auth.dependencies import get_current_user
from ..auth.schemas import ChangePasswordRequest, LoginRequest, TokenResponse, UserProfile
from ..auth.security import verify_password, create_access_token
from ..config import get_settings
from .. import models

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"


def _build_user_profile(user: models.User, db: Session) -> UserProfile:
    permissions = auth_crud.get_user_permissions(db, user.id)
    automation_ids = auth_crud.get_user_automation_ids(db, user.id)
    instance_ids = auth_crud.get_user_accessible_instance_ids(db, user.id)
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        permissions=permissions,
        automation_ids=automation_ids,
        instance_ids=instance_ids,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_crud.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    settings = get_settings()
    access_token, _ = create_access_token(str(user.id), user.role)
    refresh_token = auth_crud.create_session(db, user.id, expire_days=settings.jwt_refresh_expire_days)
    db.commit()

    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
        path="/",
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: Session = Depends(get_db),
):
    if refresh_token:
        session = auth_crud.get_active_session(db, refresh_token)
        if session:
            auth_crud.revoke_session(db, session)
            db.commit()
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth")


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")

    session = auth_crud.get_active_session(db, refresh_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada")

    user = session.user
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    settings = get_settings()

    # Rotate refresh token
    auth_crud.revoke_session(db, session)
    new_refresh_token = auth_crud.create_session(db, user.id, expire_days=settings.jwt_refresh_expire_days)
    access_token, _ = create_access_token(str(user.id), user.role)
    db.commit()

    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=new_refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
        path="/",
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.get("/me", response_model=UserProfile)
def me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _build_user_profile(user, db)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
    auth_crud.update_user(db, user, password=body.new_password)
    auth_crud.revoke_all_user_sessions(db, user.id)
    db.commit()
