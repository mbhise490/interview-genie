from pydantic import BaseModel
from typing import Optional
from interview_genie.Models.schema import InterviewFeedback


class StartInterviewRequest(BaseModel):
    resume_pdf_path: str
    target_role: str
    thread_id: str


class SubmitAnswerRequest(BaseModel):
    thread_id: str
    answer: str


class EndInterviewRequest(BaseModel):
    thread_id: str


class InterviewTurnResponse(BaseModel):
    question: Optional[str] = None
    status: str
    question_count: int
    total_score: float
    feedback: Optional[InterviewFeedback] = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = "Candidate"
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    candidate_id: str
    email: str
    full_name: str


class CandidateProfileResponse(BaseModel):
    candidate_id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    created_at: Optional[str] = None
    interviews: list = []