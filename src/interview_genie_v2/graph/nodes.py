from langgraph.graph import END

from interview_genie_v2.agents.evaluator_agent import evaluate_interview
from interview_genie_v2.agents.interview_agent import next_turn
from interview_genie_v2.graph.state import InterviewState


def interviewer_node(state: InterviewState) -> dict:
    turn = next_turn(state)
    message = {"role": "interviewer", "content": turn.question}
    dynamic = state["dynamic"]
    updated = dynamic.model_copy(
        update={
            "messages": [*dynamic.messages, message],
            "status": "completed" if turn.action == "end_interview" else dynamic.status,})
    return {"dynamic": updated}


def evaluator_node(state: InterviewState) -> dict:
    feedback = evaluate_interview(state)
    return {"dynamic": state["dynamic"].model_copy(update={"feedback": feedback, "status": "completed"})}


def route_entry(state: InterviewState) -> str:
    # "end interview" requests arrive with status already set to completed
    return "evaluator" if state["dynamic"].status == "completed" else "interviewer"


def route_after_interviewer(state: InterviewState) -> str:
    return "evaluator" if state["dynamic"].status == "completed" else END