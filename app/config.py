import os
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'maisie.db'}"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "jon")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me-before-dad-finds-out")

EXIF_TOLERANCE_MINUTES = int(os.environ.get("EXIF_TOLERANCE_MINUTES", "90"))

# The household's timezone. Servers usually run UTC, so all "what time is it"
# questions (upload stamps, checklist times, which day is "today") go through
# local_now() instead of datetime.now().
TIMEZONE = os.environ.get("TIMEZONE", "America/New_York")
TZ = ZoneInfo(TIMEZONE)


def local_now() -> datetime:
    """Naive local time in the configured timezone (matches phone EXIF times)."""
    return datetime.now(TZ).replace(tzinfo=None)

SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14  # two weeks
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Signing key for the session cookie, persisted so logins survive restarts.
_secret_file = DATA_DIR / ".secret_key"
if _secret_file.exists():
    SECRET_KEY = _secret_file.read_text().strip()
else:
    SECRET_KEY = secrets.token_hex(32)
    _secret_file.write_text(SECRET_KEY)
    _secret_file.chmod(0o600)
