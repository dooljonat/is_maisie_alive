# ismaisiealive.net

A daily proof-of-life blog for one (1) pug, demanded by one (1) nervous father.

FastAPI + SQLite. Public feed at `/`, admin dispatch desk at `/admin`.

## Features

- **Giant verdict banner** — "YES." while there's proof of life in the last 24 hours,
  degrading to "ALMOST CERTAINLY." when the blogging slips.
- **Daily dispatches** — one post per day with the dad-mandated duty checklist
  (including the verbatim requirements from The Text) and captioned photos.
- **Timestamp verification** — each upload's EXIF `DateTimeOriginal` is compared to
  the upload time. Within the tolerance window (default 90 min) the photo gets a
  "timestamp verified" badge; older EXIF gets accused of being recycled footage;
  missing EXIF (screenshots, texted photos) is flagged as a possible conspiracy.
- **Admin desk** — password-protected; create today's post, toggle duties, upload
  and delete photos.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit: set ADMIN_USERNAME / ADMIN_PASSWORD
```

## Run

```bash
uvicorn app.main:app --reload
```

Site: http://127.0.0.1:8000 · Admin: http://127.0.0.1:8000/admin

## Data

Everything lives under `data/` (created automatically): `maisie.db` (SQLite),
`uploads/` (photos), and `.secret_key` (session-cookie signing key). Back that
directory up if Maisie's legacy matters to you.

## Deploying

- Run behind HTTPS (the session cookie isn't marked `Secure` by default; if you
  terminate TLS at a proxy you can leave it, but don't run the admin over plain
  HTTP on the open internet).
- Set a strong `ADMIN_PASSWORD` in `.env`.
- Typical production command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  behind nginx/Caddy, or wrap it in a systemd unit / Docker as you prefer.

## EXIF caveat

Photos sent through most messaging apps or taken as screenshots have their EXIF
stripped, so upload straight from the camera roll for the verified badge. HEIC
isn't accepted — have your phone save/export as JPEG.
