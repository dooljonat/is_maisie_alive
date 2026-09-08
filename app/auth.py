import secrets

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config

COOKIE_NAME = "maisie_admin"

_serializer = URLSafeTimedSerializer(config.SECRET_KEY, salt="maisie-admin-session")


def check_credentials(username: str, password: str) -> bool:
    user_ok = secrets.compare_digest(username, config.ADMIN_USERNAME)
    pass_ok = secrets.compare_digest(password, config.ADMIN_PASSWORD)
    return user_ok and pass_ok


def make_session_token() -> str:
    return _serializer.dumps({"role": "admin"})


def is_admin(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer.loads(token, max_age=config.SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("role") == "admin"
