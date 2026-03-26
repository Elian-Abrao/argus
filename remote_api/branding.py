"""Branding configuration — reads from environment variables set by docker-compose from argus.yml."""
from __future__ import annotations
import os

def get_branding() -> dict:
    return {
        "platform": {
            "name": os.getenv("ARGUS_PLATFORM_NAME", "Argus"),
            "tagline": os.getenv("ARGUS_PLATFORM_TAGLINE", "Intelligent automation monitoring"),
            "logo_url": os.getenv("ARGUS_LOGO_URL", ""),
            "primary_color": os.getenv("ARGUS_PRIMARY_COLOR", "#6366f1"),
            "support_url": os.getenv("ARGUS_SUPPORT_URL", ""),
        },
        "ai": {
            "name": os.getenv("ARGUS_AI_NAME", "Argus AI"),
            "avatar_url": os.getenv("ARGUS_AI_AVATAR_URL", "/ai/avatar.webp"),
            "greeting": os.getenv("ARGUS_AI_GREETING", "Hello! How can I help you?"),
        },
    }
