from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from langgraph.types import Command

from interview_genie.api.deps import interview_app, get_current_user, get_optional_current_user
from interview_genie.api.schemas import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    EndInterviewRequest,
    InterviewTurnResponse,
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    CandidateProfileResponse,
)
from interview_genie.utils.auth import hash_password, verify_password, create_access_token
from interview_genie.database.db_conn import (
    validate_db_connection,
    save_completed_interview,
    register_candidate_user,
    get_candidate_by_email,
    get_candidate_profile,
    get_prior_feedback_for_role,
    get_candidate_id_for_thread,
)
from interview_genie.agents.evaluator_agent import evaluate_interview

router = APIRouter()


def _extract_turn_response(result: dict) -> InterviewTurnResponse:
    interview_state = result.get("interview_state")
    interrupt_data = result.get("__interrupt__")
    feedback = result.get("feedback")

    question = None
    if interrupt_data:
        question = interrupt_data[0].value.get("question")
    elif interview_state:
        if isinstance(interview_state, dict):
            status_val = interview_state.get("status", "not_started")
            conv = interview_state.get("conversation", [])
            if conv and status_val != "completed":
                last_turn = conv[-1]
                question = last_turn.get("question") if isinstance(last_turn, dict) else getattr(last_turn, "question", None)
        else:
            status_val = getattr(interview_state, "status", "not_started")
            conv = getattr(interview_state, "conversation", [])
            if conv and status_val != "completed":
                question = conv[-1].question

    if isinstance(interview_state, dict):
        status_val = interview_state.get("status", "not_started")
        question_count = interview_state.get("question_count", 0)
        total_score = float(interview_state.get("total_score", 0.0))
    elif interview_state:
        status_val = interview_state.status
        question_count = interview_state.question_count
        total_score = float(interview_state.total_score)
    else:
        status_val = "not_started"
        question_count = 0
        total_score = 0.0

    return InterviewTurnResponse(
        question=question,
        status=status_val,
        question_count=question_count,
        total_score=total_score,
        feedback=feedback,
    )


# =========================================================================
# Authentication Endpoints
# =========================================================================

@router.post("/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    """Registers a new candidate user with email and password."""
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    try:
        pwd_hash = hash_password(req.password)
        candidate = register_candidate_user(
            email=req.email,
            password_hash=pwd_hash,
            full_name=req.full_name or "Candidate",
            phone=req.phone,
        )
        token = create_access_token({"sub": candidate["candidate_id"], "email": candidate["email"]})
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            candidate_id=candidate["candidate_id"],
            email=candidate["email"],
            full_name=candidate["full_name"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")


@router.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """Authenticates candidate with email and password, returning a JWT token."""
    candidate = get_candidate_by_email(req.email)
    if not candidate or not candidate.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(req.password, candidate["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token({"sub": candidate["candidate_id"], "email": candidate["email"]})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        candidate_id=candidate["candidate_id"],
        email=candidate["email"],
        full_name=candidate["full_name"],
    )


@router.get("/auth/me", response_model=CandidateProfileResponse)
def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Returns the profile and interview history of the authenticated candidate."""
    return CandidateProfileResponse(**current_user)


# =========================================================================
# Database Diagnostic Endpoint
# =========================================================================

@router.get("/db/validate")
def validate_db():
    """Validates the SQL Server database connection and table readiness."""
    res = validate_db_connection()
    if res.get("status") != "connected":
        raise HTTPException(status_code=503, detail=res)
    return res


# =========================================================================
# Interview Endpoints
# =========================================================================

@router.post("/interview/start", response_model=InterviewTurnResponse)
def start_interview(
    req: StartInterviewRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Starts an interview session, automatically linking to authenticated candidate if logged in."""
    try:
        cand_id = current_user.get("candidate_id") if current_user else None
        config = {"configurable": {"thread_id": req.thread_id}}
        result = interview_app.invoke(
            {
                "resume_pdf_path": req.resume_pdf_path,
                "target_role": req.target_role,
                "thread_id": req.thread_id,
                "candidate_id": cand_id,
            },
            config=config,
        )
        return _extract_turn_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/answer", response_model=InterviewTurnResponse)
def submit_answer(req: SubmitAnswerRequest):
    """Submits candidate's answer and receives the next question and score."""
    try:
        config = {"configurable": {"thread_id": req.thread_id}}
        result = interview_app.invoke(Command(resume=req.answer), config=config)
        return _extract_turn_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/end", response_model=InterviewTurnResponse)
def end_interview_session(
    req: EndInterviewRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Manually ends the interview, generates feedback using evaluator_agent
    (incorporating prior feedback if candidate has past interviews for the SAME role),
    stores everything in SQL Server, and returns the final evaluation.
    """
    try:
        config = {"configurable": {"thread_id": req.thread_id}}
        state = interview_app.get_state(config)
        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        interview_state = state.values.get("interview_state")
        target_role = state.values.get("target_role", "Software Engineer")

        if not interview_state:
            raise HTTPException(status_code=400, detail="No active interview state.")

        # Update status to completed
        if hasattr(interview_state, "model_copy"):
            completed_state = interview_state.model_copy(deep=True)
            completed_state.status = "completed"
        else:
            completed_state = interview_state
            completed_state["status"] = "completed"

        # Check for prior feedback for the EXACT SAME target role
        candidate_id = (current_user.get("candidate_id") if current_user else None) or get_candidate_id_for_thread(req.thread_id)
        prior_feedback = None
        if candidate_id:
            prior_feedback = get_prior_feedback_for_role(
                candidate_id=candidate_id,
                target_role=target_role,
                exclude_thread_id=req.thread_id,
            )

        # Generate evaluation feedback (comparing against historical feedback if role matches)
        feedback = evaluate_interview(
            interview_state=completed_state,
            target_role=target_role,
            historical_feedback=prior_feedback,
        )

        # Store in SQL Server
        save_completed_interview(req.thread_id, completed_state, feedback)

        # Update LangGraph checkpointer state
        interview_app.update_state(config, {"interview_state": completed_state, "feedback": feedback})

        return _extract_turn_response({
            "interview_state": completed_state,
            "feedback": feedback,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interview/{thread_id}/status", response_model=InterviewTurnResponse)
def get_status(thread_id: str):
    """Reads interview state without advancing the turn."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = interview_app.get_state(config)
        values = dict(state.values) if state.values else {}
        if state.tasks:
            for task in state.tasks:
                if task.interrupts:
                    values["__interrupt__"] = list(task.interrupts)
                    break
        return _extract_turn_response(values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interview/{thread_id}/feedback")
def get_feedback(thread_id: str):
    """Retrieves final feedback for completed interview session."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = interview_app.get_state(config)
        feedback = state.values.get("feedback")
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not yet available — interview may still be in progress.")
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))