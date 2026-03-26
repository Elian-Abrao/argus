"""Password hashing, JWT creation/validation and refresh token utilities."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from ..config import get_settings


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Access token (JWT, short-lived)
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, role: str) -> tuple[str, datetime]:
    """Return (encoded_jwt, expires_at)."""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict | None:
    """Return payload dict or None if invalid/expired."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Refresh token (opaque, stored hashed in DB)
# ---------------------------------------------------------------------------

def generate_refresh_token() -> str:
    """Return a URL-safe random 64-character token."""
    return secrets.token_urlsafe(48)


def generate_temporary_password() -> str:
    """Generate a strong random temporary password that satisfies all complexity rules.

    Format: 3 uppercase + 3 lowercase + 3 digits + 3 specials, shuffled = 12 chars.
    Always meets the validation requirements in schemas.py.
    """
    import string
    uppers = [secrets.choice(string.ascii_uppercase) for _ in range(3)]
    lowers = [secrets.choice(string.ascii_lowercase) for _ in range(3)]
    digits = [secrets.choice(string.digits) for _ in range(3)]
    specials = [secrets.choice("@!#$%&*-_+=?") for _ in range(3)]
    pool = uppers + lowers + digits + specials
    # Shuffle with secrets-backed Fisher-Yates
    for i in range(len(pool) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        pool[i], pool[j] = pool[j], pool[i]
    return "".join(pool)


def hash_token(token: str) -> str:
    """Return SHA-256 hex digest — stored in DB instead of the raw token."""
    return hashlib.sha256(token.encode()).hexdigest()
