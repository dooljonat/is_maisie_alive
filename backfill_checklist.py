"""One-time backfill: bring today's existing post up to the current duty roster.

Rebuilds today's checklist in DEFAULT_CHECKLIST order, preserving the done
state and check-off times of items that already exist (matched by label).
Labels not in the default roster (if any) are kept at the end. Safe to run
more than once. Run from the project root: .venv/bin/python backfill_checklist.py
"""
from sqlalchemy import select

from app import config
from app.db import DEFAULT_CHECKLIST, ChecklistItem, Post, SessionLocal, init_db

init_db()
db = SessionLocal()

today = config.local_now().date()
post = db.scalar(select(Post).where(Post.day == today))
if not post:
    print(f"No post for {today} — nothing to backfill.")
    raise SystemExit(0)

existing = {item.label: item for item in post.checklist}
extras = [item for item in post.checklist if item.label not in DEFAULT_CHECKLIST]

added = [label for label in DEFAULT_CHECKLIST if label not in existing]
if not added:
    print(f"Post for {today} already has the full roster ({len(post.checklist)} items).")
    raise SystemExit(0)

# Rebuild in roster order so new items sit in their proper place, not at the end.
rebuilt = [
    ChecklistItem(
        label=label,
        done=existing[label].done if label in existing else False,
        checked_at=existing[label].checked_at if label in existing else None,
    )
    for label in DEFAULT_CHECKLIST
] + [
    ChecklistItem(label=item.label, done=item.done, checked_at=item.checked_at)
    for item in extras
]
post.checklist = rebuilt
db.commit()
print(f"Backfilled {today}: added {added}; checklist is now {len(rebuilt)} items.")
