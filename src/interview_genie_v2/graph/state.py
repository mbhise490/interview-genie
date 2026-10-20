from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from interview_genie_v2.Models.schema import EvaluationResult, KeyTopics, ResumeInfo


class StaticContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_role: str
    resume: ResumeInfo
    key_topics: KeyTopics


class Message(TypedDict):
    role: Literal["interviewer", "candidate"]
    content: str
    topic: str | None


class DynamicState(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    asked_topics: list[str] = Field(default_factory=list)
    current_topic: str | None = None
    follow_up_count: int = 0
    status: Literal["in_progress", "completed"] = "in_progress"
    feedback: EvaluationResult | None = None


class InterviewState(TypedDict):
    static: StaticContext
    dynamic: DynamicState


def initial_state(target_role: str, resume: ResumeInfo, key_topics: KeyTopics) -> InterviewState:
    return {
        "static": StaticContext(target_role=target_role, resume=resume, key_topics=key_topics),
        "dynamic": DynamicState(),}
