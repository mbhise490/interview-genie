from interview_genie_v2.graph.state import InterviewState

_sessions: dict[int, InterviewState] = {}


def get(interview_id: int) -> InterviewState | None:
    return _sessions.get(interview_id)


def put(interview_id: int, state: InterviewState) -> None:
    _sessions[interview_id] = state


def delete(interview_id: int) -> None:
    _sessions.pop(interview_id, None)
