import random
import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, config, exif_check
from .db import (
    DEFAULT_CHECKLIST,
    DEFAULT_TITLES,
    ChecklistItem,
    Comment,
    Photo,
    Post,
    get_session,
    init_db,
)

app = FastAPI(title="ismaisiealive.net")

init_db()

APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory=APP_DIR / "templates")


def humanize_since(then: datetime, now: datetime | None = None) -> str:
    now = now or config.local_now()
    seconds = max(0, int((now - then).total_seconds()))
    if seconds < 60:
        return "moments ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


# Cache-buster: CDNs (e.g. Cloudflare) cache /static aggressively, so version
# the stylesheet URL by its mtime — each deploy gets a fresh URL automatically.
templates.env.globals["css_v"] = int((APP_DIR / "static" / "style.css").stat().st_mtime)

templates.env.filters["since"] = humanize_since
templates.env.filters["clock"] = lambda dt: dt.strftime("%-I:%M %p") if dt else ""
templates.env.filters["longdate"] = lambda d: d.strftime("%A, %B %-d")


# ---------------------------------------------------------------- public feed


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_session)):
    posts = db.scalars(select(Post).order_by(Post.day.desc())).all()

    # Day numbering counts up from the first day on duty.
    if posts:
        first_day = min(p.day for p in posts)
        for p in posts:
            p.day_number = (p.day - first_day).days + 1

    status = compute_status(posts)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"posts": posts, "status": status, "is_admin": auth.is_admin(request)},
    )


def compute_status(posts: list[Post]) -> dict:
    if not posts:
        return {
            "verdict": "PRESUMABLY.",
            "tone": "unknown",
            "detail": "The blog hasn't started yet. She's fine. Probably napping.",
        }
    latest = max(p.latest_activity for p in posts)
    hours = (config.local_now() - latest).total_seconds() / 3600
    if hours < 24:
        return {
            "verdict": "YES.",
            "tone": "alive",
            "detail": f"Last proof of life: {humanize_since(latest)}. You can relax, Dad.",
        }
    return {
        "verdict": "ALMOST CERTAINLY.",
        "tone": "stale",
        "detail": (
            f"It's been {humanize_since(latest)[:-4]} since the last update. "
            "She's fine — I'm just behind on blogging."
        ),
    }


# ------------------------------------------------------------ guest comments


@app.post("/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    author: str = Form(...),
    body: str = Form(...),
    website: str = Form(""),  # honeypot: humans never see this field
    db: Session = Depends(get_session),
):
    post = db.get(Post, post_id)
    author = author.strip()[:60]
    body = body.strip()[:1000]
    if post and author and body and not website:
        db.add(Comment(post_id=post.id, author=author, body=body))
        db.commit()
    return RedirectResponse(f"/#post-{post_id}", status_code=303)


# Note: there is deliberately no comment-delete route. Guest comments are an
# immutable public record — the management cannot silence its critics.


# ---------------------------------------------------------------------- auth


@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request):
    if auth.is_admin(request):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/admin/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not auth.check_credentials(username, password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Nope. Are you Dad? Dad, is that you?"},
            status_code=401,
        )
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_session_token(),
        max_age=config.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/admin/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


def _guard(request: Request) -> RedirectResponse | None:
    if not auth.is_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    return None


def _back(request: Request) -> RedirectResponse:
    """Redirect to the same-site page the form was submitted from."""
    referer = request.headers.get("referer", "")
    path = "/" + referer.split("/", 3)[3] if referer.count("/") >= 3 else "/admin"
    if not path.startswith("/") or path.startswith("//"):
        path = "/admin"
    return RedirectResponse(path, status_code=303)


# --------------------------------------------------------------------- admin


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_session)):
    if r := _guard(request):
        return r
    today = config.local_now().date()
    post = db.scalar(select(Post).where(Post.day == today))
    recent = db.scalars(select(Post).order_by(Post.day.desc()).limit(14)).all()
    return templates.TemplateResponse(
        request, "admin.html", {"post": post, "today": today, "recent": recent}
    )


@app.post("/admin/posts/today")
def create_today_post(request: Request, db: Session = Depends(get_session)):
    if r := _guard(request):
        return r
    today = config.local_now().date()
    if not db.scalar(select(Post).where(Post.day == today)):
        post = Post(day=today, title=random.choice(DEFAULT_TITLES), body="")
        post.checklist = [ChecklistItem(label=label) for label in DEFAULT_CHECKLIST]
        db.add(post)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/posts/{post_id}/edit", response_class=HTMLResponse)
def edit_post_page(request: Request, post_id: int, db: Session = Depends(get_session)):
    if r := _guard(request):
        return r
    post = db.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "post_edit.html", {"post": post})


@app.post("/admin/posts/{post_id}/update")
def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    body: str = Form(""),
    db: Session = Depends(get_session),
):
    if r := _guard(request):
        return r
    post = db.get(Post, post_id)
    if post:
        post.title = title.strip() or post.title
        post.body = body.strip()
        post.updated_at = config.local_now()
        db.commit()
    return _back(request)


@app.post("/admin/checklist/{item_id}/toggle")
def toggle_checklist(request: Request, item_id: int, db: Session = Depends(get_session)):
    if r := _guard(request):
        return r
    item = db.get(ChecklistItem, item_id)
    if item:
        item.done = not item.done
        item.checked_at = config.local_now() if item.done else None
        item.post.updated_at = config.local_now()
        db.commit()
    return _back(request)


@app.post("/admin/posts/{post_id}/photos")
async def upload_photos(
    request: Request,
    post_id: int,
    caption: str = Form(""),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_session),
):
    if r := _guard(request):
        return r
    post = db.get(Post, post_id)
    if not post:
        return RedirectResponse("/admin", status_code=303)

    # Each file gets its own EXIF timestamp check; a shared caption (if any)
    # applies to the whole batch. Bad files are skipped, good ones still land.
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in config.ALLOWED_EXTENSIONS:
            continue
        contents = await file.read()
        if not contents or len(contents) > config.MAX_UPLOAD_BYTES:
            continue

        filename = f"{uuid.uuid4().hex}{ext}"
        dest = config.UPLOAD_DIR / filename
        dest.write_bytes(contents)

        uploaded_at = config.local_now()
        taken_at = exif_check.read_taken_at(dest)
        verified = exif_check.is_verified(
            uploaded_at, taken_at, config.EXIF_TOLERANCE_MINUTES
        )
        db.add(
            Photo(
                post_id=post.id,
                filename=filename,
                caption=caption.strip(),
                uploaded_at=uploaded_at,
                taken_at=taken_at,
                verified=verified,
            )
        )
        post.updated_at = uploaded_at
    db.commit()
    return _back(request)


@app.post("/admin/posts/{post_id}/delete")
def delete_post(request: Request, post_id: int, db: Session = Depends(get_session)):
    if r := _guard(request):
        return r
    post = db.get(Post, post_id)
    if post:
        for photo in post.photos:
            (config.UPLOAD_DIR / photo.filename).unlink(missing_ok=True)
        db.delete(post)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/photos/{photo_id}/delete")
def delete_photo(request: Request, photo_id: int, db: Session = Depends(get_session)):
    if r := _guard(request):
        return r
    photo = db.get(Photo, photo_id)
    if photo:
        (config.UPLOAD_DIR / photo.filename).unlink(missing_ok=True)
        db.delete(photo)
        db.commit()
    return _back(request)
