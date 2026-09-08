"""Read a photo's EXIF capture time and compare it against upload time.

Photos straight off a phone camera carry DateTimeOriginal; screenshots and
images re-saved by messaging apps usually don't. That difference is the whole
"timestamp verified" gag.
"""
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

# EXIF tag ids: 36867 = DateTimeOriginal, 36868 = DateTimeDigitized, 306 = DateTime
_DATETIME_TAGS = (36867, 36868, 306)
_EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"


def read_taken_at(path: Path) -> datetime | None:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            # DateTimeOriginal/Digitized live in the EXIF IFD; 306 in the base IFD.
            values = dict(exif)
            try:
                values.update(exif.get_ifd(0x8769))
            except Exception:
                pass
            for tag in _DATETIME_TAGS:
                raw = values.get(tag)
                if raw:
                    return datetime.strptime(str(raw).strip("\x00 "), _EXIF_FORMAT)
    except Exception:
        return None
    return None


def is_verified(uploaded_at: datetime, taken_at: datetime | None, tolerance_minutes: int) -> bool:
    if taken_at is None:
        return False
    return abs(uploaded_at - taken_at) <= timedelta(minutes=tolerance_minutes)
