from pydantic import BaseModel, Field
from typing import Literal

class Project(BaseModel):
    name: str = Field(..., description="Project title as written in the resume.")
    description: str = Field(..., description="One or two sentences on what the project does.")
    technologies: list[str] = Field(..., description="Tools, languages and libraries used in this project.")

class Experience(BaseModel):
    role: str = Field(..., description="Job title or internship role.")
    organization: str = Field(..., description="Company or organization name.")
    duration: str = Field(..., description="Time period as written, or an empty string if not given.")
    responsibilities: list[str] = Field(..., description="Key responsibilities and outcomes.")

class ResumeInfo(BaseModel):
    is_valid: bool = Field(..., description="True only if the text is actually a resume or CV.")
    invalid_reason: str | None = Field(..., description="Why it is not a resume, or null if valid.")

    candidate_name: str = Field(..., description="Candidate's name, or an empty string if not found.")
    skills: list[str] = Field(..., description="Skills explicitly listed or clearly demonstrated.")
    projects: list[Project] = Field(..., description="Projects described in the resume.")
    experience: list[Experience] = Field(..., description="Work experience and internships.")
    certifications: list[str] = Field(..., description="Certifications obtained.")
    achievements: list[str] = Field(..., description="Notable achievements and awards.")
    other_relevant_info: list[str] = Field(..., description="Education, publications or anything else relevant.")

class KeyTopic(BaseModel):
    topic: str = Field(..., description="Main topic to discuss, e.g. 'SQL' or 'Interview Genie project'.")
    category: Literal["role_fundamentals", "technical_skill", "project_deep_dive", "experience", "behavioral"]
    source: Literal["role", "resume", "both"] = Field(..., description="Whether the topic comes from the target role, the resume, or both.")
    reason: str = Field(..., description="One sentence on why this topic must be covered in the interview.")

class KeyTopics(BaseModel):
    topics: list[KeyTopic] = Field(..., description="Essential topics for the interview, ordered by importance.")

class InterviewerTurn(BaseModel):
    action: Literal["ask_new_topic", "follow_up", "end_interview"]
    topic: str | None = Field(..., description="Topic name this question belongs to, or null when ending.")
    question: str = Field(..., description="What the interviewer says next: one question, or a closing message.")

class Observation(BaseModel):
    point: str = Field(..., description="One specific strength or weakness.")

class ImprovementArea(BaseModel):
    area: str = Field(..., description="Short name, e.g. 'Structuring answers'.")
    why: str = Field(..., description="What in the interview shows this needs work.")
    how_to_improve: str = Field(..., description="One concrete, practical action the candidate can take.")

class EvaluationResult(BaseModel):
    """What the LLM returns."""
    summary: str = Field(..., description="3 to 4 sentence overall assessment.")
    strengths: list[Observation]
    weaknesses: list[Observation]
    communication_feedback: str = Field(..., description="Feedback on clarity, structure, conciseness, vocabulary and completeness of answers.")
    improvement_areas: list[ImprovementArea]