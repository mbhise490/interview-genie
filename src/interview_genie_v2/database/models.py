from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, UnicodeText


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    __tablename__ = "users"
    user_id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=25)
    email: str = Field(max_length=255, unique=True)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=_utcnow)

class Interview(SQLModel, table=True):
    __tablename__ = "interview"
    interview_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id")
    target_role: str = Field(max_length=200)
    resume_text: str = Field(sa_column=Column(UnicodeText, nullable=False))
    resume_parsed: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    key_topics: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    interview_script: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    interview_state: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    status: str = Field(default="in_progress", max_length=20)
    created_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = Field(default=None)


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"
    feedback_id: int | None = Field(default=None, primary_key=True)
    interview_id: int = Field(foreign_key="interview.interview_id", unique=True)
    user_id: int = Field(foreign_key="users.user_id")
    strength: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    weakness: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    other_feedback: str | None = Field(default=None, sa_column=Column(UnicodeText, nullable=True))
    created_at: datetime = Field(default_factory=_utcnow)
