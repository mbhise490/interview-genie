from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Literal

from interview_genie_v2.Models.schema import ImprovementArea, Observation



class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=25)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  

class UserOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr

class InterviewOut(BaseModel):
    interview_id: int
    target_role: str
    status: str
    resume_chars: int
    created_at: datetime

class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)

class TurnOut(BaseModel):
    interview_id: int
    status: Literal["in_progress", "completed"]
    message: str                 # the next question, or the closing message

class InterviewSummary(BaseModel):
    interview_id: int
    target_role: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class FeedbackDetails(BaseModel):
    summary: str
    communication_feedback: str
    improvement_areas: list[ImprovementArea]


class FeedbackOut(BaseModel):
    interview_id: int
    target_role: str
    completed_at: datetime | None
    strengths: list[Observation]
    weaknesses: list[Observation]
    details: FeedbackDetails
    transcript: list[dict]