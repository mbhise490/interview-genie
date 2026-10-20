from langgraph.graph import END, START, StateGraph

from interview_genie_v2.graph.nodes import (
    evaluator_node,
    interviewer_node,
    route_after_interviewer,
    route_entry,)
from interview_genie_v2.graph.state import InterviewState


def build_graph():
    graph = StateGraph(InterviewState)
    graph.add_node("interviewer", interviewer_node)
    graph.add_node("evaluator", evaluator_node)

    graph.add_conditional_edges(START, route_entry, {"interviewer": "interviewer", "evaluator": "evaluator"})
    graph.add_conditional_edges("interviewer", route_after_interviewer, {"evaluator": "evaluator", END: END})
    graph.add_edge("evaluator", END)
    return graph.compile()

interview_graph = build_graph()