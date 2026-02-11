import hashlib
import hmac
import secrets

from app.core.settings import settings


def generate_token() -> str:
    # коротко, безопасно, удобно для URL
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).digest()
