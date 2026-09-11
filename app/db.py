from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from . import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Default post titles. A new dispatch picks one at random, because writing
# "Maisie remains alive" 14 days in a row is its own kind of cry for help.
DEFAULT_TITLES = [
    "Maisie remains alive",
    "Yep, still alive",
    "Maisie is, in fact, still alive",
    "Still alive. Still snoring.",
    "Update: pug operational",
    "No news, which is the good kind",
    "Alive, unimpressed",
    "Vital signs: aggressively normal",
    "The pug endures",
    "Another day, another unremarkable pug",
    "She lives. She judges.",
    "Confirmed: not dead",
    "Breathing, as usual",
    "Maisie: 1, Entropy: 0",
    "Status quo maintained",
    "All limbs accounted for",
    "Suspiciously fine",
    "Yes, Dad. She's fine.",
]

# The dad-mandated duties, verbatim where it counts.
DEFAULT_CHECKLIST = [
    "Let Maisie into my room (per The Text)",
    "Did NOT leave her in the pen the whole time (also per The Text)",
    "Breakfast served",
    "Lunch served",
    "Dinner served",
    "Gave medicine",
    "Water bowl: full",
    "Walk / neighborhood sniff patrol",
    "Pee peed",
    "Poo poo'd",
    "Visual confirmation: still alive",
]


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=config.local_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=config.local_now, onupdate=config.local_now
    )

    checklist: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="ChecklistItem.id"
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="post", cascade="all, delete-orphan",
        order_by="Photo.uploaded_at.desc(), Photo.id.desc()"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="Comment.created_at"
    )

    @property
    def done_count(self) -> int:
        return sum(1 for item in self.checklist if item.done)

    @property
    def photo_batches(self) -> list[list["Photo"]]:
        """Photos grouped into upload batches, newest batch first.

        Each batch renders as one carousel under a shared caption. Photos
        predating batch ids (batch_id None) each stand alone.
        """
        batches: list[list[Photo]] = []
        for photo in self.photos:
            if (
                batches
                and photo.batch_id is not None
                and batches[-1][0].batch_id == photo.batch_id
            ):
                batches[-1].append(photo)
            else:
                batches.append([photo])
        return batches

    @property
    def latest_activity(self) -> datetime:
        times = [self.updated_at or self.created_at]
        times += [p.uploaded_at for p in self.photos]
        return max(times)


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    label: Mapped[str] = mapped_column(String(300))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    post: Mapped[Post] = relationship(back_populates="checklist")


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    filename: Mapped[str] = mapped_column(String(120))
    caption: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=config.local_now)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Photos uploaded together share a batch id and display as one carousel.
    batch_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    post: Mapped[Post] = relationship(back_populates="photos")

    @property
    def verification_status(self) -> str:
        """One of: 'verified', 'mismatch', 'no_exif'."""
        if self.taken_at is None:
            return "no_exif"
        return "verified" if self.verified else "mismatch"


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    author: Mapped[str] = mapped_column(String(60))
    body: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=config.local_now)

    post: Mapped[Post] = relationship(back_populates="comments")


def init_db() -> None:
    Base.metadata.create_all(engine)
    # Lightweight migration: create_all doesn't add columns to existing tables,
    # so databases from before checklist timestamps need the column bolted on.
    with engine.connect() as conn:
        from sqlalchemy import text

        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(checklist_items)"))]
        if "checked_at" not in cols:
            conn.execute(text("ALTER TABLE checklist_items ADD COLUMN checked_at DATETIME"))
            conn.commit()

        photo_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(photos)"))]
        if "batch_id" not in photo_cols:
            conn.execute(text("ALTER TABLE photos ADD COLUMN batch_id VARCHAR(32)"))
            conn.commit()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
