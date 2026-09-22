from langgraph import graph
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from interview_genie.graph.state import InterviewGraphState
from interview_genie.graph.nodes import (
    extract_resume_node, parse_resume_node, generate_prep_node, init_context_node,
    ask_question_node, wait_for_answer_node, should_continue, end_node,evaluate_node
)


def build_interview_graph():
    graph = StateGraph(InterviewGraphState)

    graph.add_node("extract_resume", extract_resume_node)
    graph.add_node("parse_resume", parse_resume_node)
    graph.add_node("generate_prep", generate_prep_node)
    graph.add_node("init_context", init_context_node)
    graph.add_node("ask_question", ask_question_node)
    graph.add_node("wait_for_answer", wait_for_answer_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("end_interview", end_node)

    graph.add_edge(START, "extract_resume")
    graph.add_edge("extract_resume", "parse_resume")
    graph.add_edge("parse_resume", "generate_prep")
    graph.add_edge("generate_prep", "init_context")
    graph.add_edge("init_context", "ask_question")

    graph.add_conditional_edges("ask_question", should_continue, {"continue": "wait_for_answer", "end": "end_interview"})
    graph.add_edge("wait_for_answer", "ask_question")
    graph.add_edge("end_interview", "evaluate")
    graph.add_edge("evaluate", END)
    return graph.compile(checkpointer=MemorySaver()) 