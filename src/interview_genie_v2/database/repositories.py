from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from interview_genie_v2.database.models import Feedback, Interview, User


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def create_user(session: Session, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_interview(session: Session, user_id: int, target_role: str, resume_text: str,resume_parsed: str,key_topics: str,) -> Interview:
    interview = Interview( user_id=user_id, target_role=target_role,resume_text=resume_text,resume_parsed=resume_parsed,key_topics=key_topics, )
    session.add(interview)
    session.commit()
    session.refresh(interview)
    return interview


def get_interview_for_user(session: Session, interview_id: int, user_id: int) -> Interview | None:
    return session.exec(select(Interview).where(Interview.interview_id == interview_id, Interview.user_id == user_id,)).first()


def save_interview_progress(session: Session, interview: Interview, script_json: str) -> None:
    if interview.status != "in_progress":
        raise ValueError("Cannot save progress for a completed interview.")
    interview.interview_script = script_json
    session.add(interview)
    session.commit()


def complete_interview_with_feedback(session: Session,interview: Interview,script_json: str,feedback_cols: dict[str, str],) -> Feedback:
    """Save the final transcript, completion status, and feedback atomically."""
    if interview.status == "completed":
        raise ValueError("This interview is already completed.")

    interview.interview_script = script_json
    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)

    feedback = Feedback(interview_id=interview.interview_id,user_id=interview.user_id,strength=feedback_cols["strength"],weakness=feedback_cols["weakness"],other_feedback=feedback_cols["other_feedback"],)
    session.add(interview)
    session.add(feedback)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Feedback already exists for this interview.")
    session.refresh(feedback)
    return feedback


def get_feedback_for_interview(session: Session, interview_id: int) -> Feedback | None:
    return session.exec(select(Feedback).where(Feedback.interview_id == interview_id)).first()

def list_interviews_for_user(session: Session, user_id: int):
    # selects columns only, so the large resume_text is not loaded for every row
    stmt = (select(
            Interview.interview_id,
            Interview.target_role,
            Interview.status,
            Interview.created_at,
            Interview.completed_at,
            Feedback.other_feedback,).join(Feedback, Feedback.interview_id == Interview.interview_id, isouter=True)
        .where(Interview.user_id == user_id)
        .order_by(Interview.created_at.desc()))
    return session.exec(stmt).all()