from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Annotated
from operator import add


class ResumeInfo(BaseModel):
    candidate_info: str = Field(..., description="Candidate's personal information like name, contact details, and address.")
    skills: str = Field(..., description="List of skills possessed by the candidate.")
    education: str = Field(..., description="Educational background of the candidate.")
    projects: str = Field(..., description="Details of projects undertaken by the candidate.")
    experience: str = Field(..., description="Professional experience of the candidate.")
    certifications: str = Field(..., description="Certifications obtained by the candidate.")
    achievements: str = Field(..., description="Notable achievements of the candidate.")
    other_info: str = Field(..., description="Any other relevant information about the candidate.")


class Topic(BaseModel):
    topic: str = Field(..., description="Specific interview topic/subtopic, e.g. 'file handling', 'joins', 'decorators'.")
    level: Literal["basic", "intermediate", "advanced"] = Field(..., description="Difficulty level of this topic.")


class SkillTopics(BaseModel):
    skill: str = Field(..., description="Skill or resume section name, e.g. 'Python', 'SQL', 'Excel'.")
    topics: List[Topic] = Field(..., description="Important topics for this skill, each tagged with basic/intermediate/advanced level.")


class InterviewPrep(BaseModel):
    skill_topics: List[SkillTopics] = Field(default_factory=list, description="List of skill-wise topics, each divided by difficulty level.")
    project_questions: List[str] = Field(default_factory=list, description="Interview questions specifically based on the candidate's projects listed in the resume.")
    role_specific_questions: List[str] = Field(default_factory=list, description="Scenario-based or role-specific interview questions tailored to the target role, derived from the candidate's resume and the target role requirements.")


class InterviewPrepSchema(BaseModel):
    skill_topics: List[SkillTopics] = Field(default_factory=list, description="List of skill-wise topics, each divided by difficulty level.")
    project_questions: List[str] = Field(default_factory=list, description="Interview questions specifically based on the candidate's projects listed in the resume.")
    role_specific_questions: List[str] = Field(default_factory=list, description="Scenario-based or role-specific interview questions tailored to the target role, derived from the candidate's resume and the target role requirements.")


class StaticInterviewContext(BaseModel):
    """Everything that stays fixed for the whole interview session — built once, reused every turn."""
    target_role: str = Field(..., description="The job role the candidate is being interviewed for.")
    resume_info: ResumeInfo = Field(..., description="Structured resume information for the candidate.")
    interview_prep: InterviewPrep = Field(..., description="Skill-wise topics and project-based questions to draw questions from.")


class ConversationTurn(BaseModel):
    question: str = Field(..., description="Question asked to the candidate.")
    answer: Optional[str] = Field(None, description="Candidate's answer to the question.")
    score: Optional[float] = Field(None, description="Score for this specific answer, e.g. 0-10.")


class InterviewState(BaseModel):
    status: Literal["not_started", "in_progress", "completed"] = Field("not_started", description="Current status of the interview session.")
    conversation: Annotated[List[ConversationTurn], add] = Field(default_factory=list, description="Full conversation history so far, in order.")
    total_score: float = Field(0.0, description="Sum of scores across all answered questions.")
    question_count: int = Field(0, description="Total number of questions asked so far.")


class NextQuestion(BaseModel):
    question: str = Field(..., description="The next thing the interviewer says to the candidate — may include a brief natural reaction to their last answer before the new question.")
    score: Optional[float] = Field(None, description="Score (0-10) for the candidate's previous answer, if one was provided.")

class StrengthArea(BaseModel):
    area: str = Field(..., description="Skill/topic the candidate performed well in.")
    reason: str = Field(..., description="Why this is a strength, based on their actual answers.")


StrongArea = StrengthArea  # Alias for compatibility


class ImprovementArea(BaseModel):
    area: str = Field(..., description="Skill/topic the candidate needs to improve.")
    reason: str = Field(..., description="What was lacking, based on their actual answers.")
    suggestion: str = Field(..., description="Concrete suggestion on how to improve in this area.")


class InterviewFeedback(BaseModel):
    target_role: str = Field(..., description="The job role the candidate was being evaluated for.")
    overall_score: float = Field(..., description="Overall performance score out of 10.")
    overall_summary: str = Field(..., description="A few sentences summarizing overall performance.")
    strong_areas: List[StrengthArea] = Field(default_factory=list, description="Skills/topics the candidate handled well.")
    improvement_areas: List[ImprovementArea] = Field(default_factory=list, description="Skills/topics the candidate needs to work on.")
    role_fit_notes: str = Field(..., description="Other important things relevant to whether this candidate fits the target role — e.g. communication style, depth vs breadth, problem-solving approach, gaps against typical role expectations.")
    recommendation: Literal["strong_fit", "moderate_fit", "needs_improvement", "not_a_fit"] = Field(..., description="Overall hiring-readiness signal for this role based on the interview.")
    historical_progress: Optional[str] = Field(None, description="Detailed progress and growth comparison against previous interview(s) for the same target role, if available.")