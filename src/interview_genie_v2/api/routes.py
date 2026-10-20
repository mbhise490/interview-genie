import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from openai import OpenAIError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from interview_genie_v2.Models.schema import KeyTopics, ResumeInfo
from interview_genie_v2.agents.interview_prep import extract_key_topics
from interview_genie_v2.agents.resume_parser import parse_resume
from interview_genie_v2.api.deps import get_current_user
from interview_genie_v2.api.schemas import AnswerRequest,FeedbackOut, InterviewOut,InterviewSummary,RegisterRequest,TurnOut,UserOut
from interview_genie_v2.database.db_conn import get_session
from interview_genie_v2.database.models import Interview, User
from interview_genie_v2.database.repositories import complete_interview_with_feedback, create_interview, create_user, get_feedback_for_interview, get_interview_for_user, get_user_by_email, list_interviews_for_user

from interview_genie_v2.graph.build_graph import interview_graph
from interview_genie_v2.graph.session_store import delete, get, put
from interview_genie_v2.graph.state import InterviewState, initial_state
from interview_genie_v2.utils.auth import hash_password
from interview_genie_v2.utils.pdf import ResumeExtractionError, extract_resume_text

logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024
LLM_ERRORS = (OpenAIError, ValueError, ValidationError)
UNAVAILABLE_SESSION_MESSAGE = "This interview session is unavailable. Please start a new interview."

router = APIRouter(prefix="/auth", tags=["auth"])
interview_router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, session: Annotated[Session, Depends(get_session)]):
    if get_user_by_email(session, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    try:
        return create_user(session, body.username, body.email, hash_password(body.password))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")


@router.post("/login", response_model=UserOut)
def login(user: Annotated[User, Depends(get_current_user)]):
    return user


def _load_in_progress(session: Session, interview_id: int, user: User) -> Interview:
    interview = get_interview_for_user(session, interview_id, user.user_id)
    if interview is None:
        raise HTTPException(404, "Interview not found.")
    if interview.status != "in_progress":
        raise HTTPException(409, "This interview is already finished.")
    if not interview.resume_parsed:
        raise HTTPException(409, "This interview is not ready.")
    if not interview.key_topics:
        raise HTTPException(409, "Interview topics are not ready.")
    return interview


def _turn_out(interview_id: int, state: InterviewState, message: str) -> TurnOut:
    dynamic = state["dynamic"]
    return TurnOut(
        interview_id=interview_id,
        status=dynamic.status,
        message=message,)


def _finish(
    session: Session, interview: Interview, result: InterviewState, message: str) -> TurnOut:
    feedback = result["dynamic"].feedback
    if feedback is None:
        logger.error("Interview %s finished without feedback", interview.interview_id)
        raise HTTPException(502, "Could not generate feedback. Please try again.")

    full = feedback.model_dump(mode="json")
    feedback_cols = {
        "strength": json.dumps(full.pop("strengths")),
        "weakness": json.dumps(full.pop("weaknesses")),
        "other_feedback": json.dumps(full),
    }
    try:
        complete_interview_with_feedback(
            session,
            interview,
            json.dumps(result["dynamic"].messages, ensure_ascii=False),
            feedback_cols,)
    except ValueError as exc:
        logger.warning("Could not complete interview %s: %s", interview.interview_id, exc)
        raise HTTPException(409, "This interview could not be completed.")
    delete(interview.interview_id)
    return _turn_out(interview.interview_id, result, message)


@interview_router.get("", response_model=list[InterviewSummary])
def list_interviews(user: Annotated[User, Depends(get_current_user)],session: Annotated[Session, Depends(get_session)],):
    return [
        InterviewSummary(
            interview_id=row.interview_id,
            target_role=row.target_role,
            status=row.status,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )
        for row in list_interviews_for_user(session, user.user_id)
    ]


@interview_router.post("", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
def start_interview(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    target_role: Annotated[str, Form(min_length=2, max_length=200)],
    resume: Annotated[UploadFile, File()],):
    role = target_role.strip()
    if len(role) < 2:
        raise HTTPException(422, "Target role is too short.")

    session.commit()
    is_pdf_name = (resume.filename or "").lower().endswith(".pdf")
    if resume.content_type != "application/pdf" and not is_pdf_name:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are supported.")

    data = resume.file.read(MAX_RESUME_BYTES + 1)
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(413, "Resume must be under 5 MB.")

    try:
        resume_text = extract_resume_text(data)
    except ResumeExtractionError as exc:
        raise HTTPException(422, str(exc))

    try:
        parsed = parse_resume(resume_text)
    except LLM_ERRORS:
        logger.exception("Resume parsing failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not analyse the resume right now. Please try again.",)
    if not parsed.is_valid:
        raise HTTPException(
            422,
            parsed.invalid_reason or "The uploaded file does not look like a resume.",)
    if not (parsed.skills or parsed.projects or parsed.experience):
        raise HTTPException(
            422,
            "No skills, projects or experience found in the resume. "
            "Please upload a more complete version.",)
    try:
        key_topics = extract_key_topics(parsed, role)
    except LLM_ERRORS:
        logger.exception("Interview topic preparation failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not prepare interview topics right now. Please try again.",)
    interview = create_interview(
        session,
        user.user_id,
        role,
        resume_text,
        parsed.model_dump_json(),
        key_topics.model_dump_json(),)
    return InterviewOut(
        interview_id=interview.interview_id,
        target_role=interview.target_role,
        status=interview.status,
        resume_chars=len(resume_text),
        created_at=interview.created_at,)


@interview_router.post("/{interview_id}/start", response_model=TurnOut)
def begin_interview(interview_id: int,user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],):
    interview = _load_in_progress(session, interview_id, user)
    state = get(interview_id)
    if state is not None:
        messages = state["dynamic"].messages
        if messages and messages[-1]["role"] == "interviewer":
            return _turn_out(interview_id, state, messages[-1]["content"])
        raise HTTPException(409, "Interview already started. Send your answer instead.")

    target_role = interview.target_role
    resume_info = ResumeInfo.model_validate_json(interview.resume_parsed)
    key_topics = KeyTopics.model_validate_json(interview.key_topics)
    session.commit()
    state = initial_state(target_role, resume_info, key_topics)
    try:
        result = interview_graph.invoke(state)
    except LLM_ERRORS:
        logger.exception("Starting interview %s failed", interview_id)
        raise HTTPException(502, "Could not start the interview right now. Please try again.")
    dynamic = result["dynamic"]
    message = dynamic.messages[-1]["content"]
    if dynamic.status == "completed":
        return _finish(session, interview, result, message)
    put(interview_id, result)
    return _turn_out(interview_id, result, message)


@interview_router.post("/{interview_id}/answer", response_model=TurnOut)
def submit_answer(interview_id: int,body: AnswerRequest,user: Annotated[User, Depends(get_current_user)],session: Annotated[Session, Depends(get_session)],):
    text = body.answer.strip()
    if not text:
        raise HTTPException(422, "Answer cannot be empty.")

    interview = _load_in_progress(session, interview_id, user)
    state = get(interview_id)
    if state is None:
        raise HTTPException(409, UNAVAILABLE_SESSION_MESSAGE)

    dynamic = state["dynamic"]
    if not dynamic.messages or dynamic.messages[-1]["role"] != "interviewer":
        raise HTTPException(409, "There is no open question. Call /start first.")
    session.commit()
    state = {
        "static": state["static"],
        "dynamic": dynamic.model_copy(
            update={"messages": [
                    *dynamic.messages,
                    {"role": "candidate", "content": text},]}),}
    try:
        result = interview_graph.invoke(state)
    except LLM_ERRORS:
        logger.exception("Processing answer for interview %s failed", interview_id)
        raise HTTPException(502, "Could not process your answer right now. Please resend it.")
    message = result["dynamic"].messages[-1]["content"]
    if result["dynamic"].status == "completed":
        return _finish(session, interview, result, message)
    put(interview_id, result)
    return _turn_out(interview_id, result, message)


@interview_router.post("/{interview_id}/end", response_model=TurnOut)
def end_interview(interview_id: int, user: Annotated[User, Depends(get_current_user)],session: Annotated[Session, Depends(get_session)],):
    interview = _load_in_progress(session, interview_id, user)
    state = get(interview_id)
    if state is None:
        raise HTTPException(409, UNAVAILABLE_SESSION_MESSAGE)
    dynamic = state["dynamic"]
    if not any(message["role"] == "candidate" for message in dynamic.messages):
        raise HTTPException(422, "Answer at least one question before ending the interview.")

    session.commit()
    state = {"static": state["static"],"dynamic": dynamic.model_copy(update={"status": "completed"}),}
    try:
        result = interview_graph.invoke(state)
    except LLM_ERRORS:
        logger.exception("Ending interview %s failed", interview_id)
        raise HTTPException(502, "Could not generate feedback right now. Please try again.")
    return _finish(session, interview, result, "Interview ended. Your feedback is ready.")


@interview_router.get("/{interview_id}/feedback", response_model=FeedbackOut)
def get_feedback(interview_id: int,user: Annotated[User, Depends(get_current_user)],session: Annotated[Session, Depends(get_session)],):
    interview = get_interview_for_user(session, interview_id, user.user_id)
    if interview is None:
        raise HTTPException(404, "Interview not found.")
    feedback = get_feedback_for_interview(session, interview_id)
    if feedback is None:
        raise HTTPException(409, "Feedback is not ready. The interview is not finished yet.")

    return FeedbackOut(
        interview_id=interview_id,
        target_role=interview.target_role,
        completed_at=interview.completed_at,
        strengths=json.loads(feedback.strength or "[]"),
        weaknesses=json.loads(feedback.weakness or "[]"),
        details=json.loads(feedback.other_feedback or "{}"),
        transcript=json.loads(interview.interview_script or "[]"),)
