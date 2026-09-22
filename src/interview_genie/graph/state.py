from typing import Optional
from pydantic import BaseModel, Field
from interview_genie.Models.schema import StaticInterviewContext, InterviewState, InterviewFeedback


class InterviewGraphState(BaseModel):
    thread_id: Optional[str] = None
    candidate_id: Optional[str] = None
    resume_pdf_path: Optional[str] = None
    target_role: Optional[str] = None
    resume_text: Optional[str] = None
    static_context: Optional[StaticInterviewContext] = None
    static_context_str: Optional[str] = None
    interview_state: InterviewState = Field(default_factory=InterviewState)
    candidate_answer: Optional[str] = None
    feedback: Optional[InterviewFeedback] = None