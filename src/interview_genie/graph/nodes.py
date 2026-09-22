import json
from interview_genie.Models.schema import ResumeInfo, InterviewPrep, StaticInterviewContext, ConversationTurn, NextQuestion
from interview_genie.agents.resume_parser import extract_resume_text, parse_resume_with_llm
from interview_genie.agents.interview_prep import generate_interview_prep
from interview_genie.agents.interview_agent import interview_agent, build_static_context
from interview_genie.graph.state import InterviewGraphState
from langgraph.types import interrupt


def extract_resume_node(state: InterviewGraphState) -> dict:
    text = extract_resume_text(state.resume_pdf_path)
    return {"resume_text": text}


def parse_resume_node(state: InterviewGraphState) -> dict:
    parsed_json_str = parse_resume_with_llm(state.resume_text or "")
    try:
        data = json.loads(parsed_json_str) if parsed_json_str else {}
    except Exception:
        data = {}

    defaults = {
        "candidate_info": "Not specified",
        "skills": "Not specified",
        "education": "Not specified",
        "projects": "Not specified",
        "experience": "Not specified",
        "certifications": "Not specified",
        "achievements": "Not specified",
        "other_info": "Not specified",
    }
    for field, default_val in defaults.items():
        if not data.get(field):
            data[field] = default_val

    resume_info = ResumeInfo(**data)
    return {"static_context": StaticInterviewContext(
        target_role=state.target_role or "Software Engineer",
        resume_info=resume_info,
        interview_prep=InterviewPrep(skill_topics=[], project_questions=[], role_specific_questions=[]),
    )}


from langchain_core.runnables import RunnableConfig
from interview_genie.agents.evaluator_agent import evaluate_interview
from interview_genie.database.db_conn import (
    save_initial_interview,
    update_interview_turn,
    save_completed_interview,
)


def generate_prep_node(state: InterviewGraphState, config: RunnableConfig = None) -> dict:
    resume_info_dict = state.static_context.resume_info.model_dump() if state.static_context else {}
    target_role = state.target_role or (state.static_context.target_role if state.static_context else "Software Engineer")
    prep_json_str = generate_interview_prep(resume_info_dict, target_role)

    try:
        prep_data = json.loads(prep_json_str) if prep_json_str else {}
    except Exception:
        prep_data = {}

    interview_prep = InterviewPrep(
        skill_topics=prep_data.get("skill_topics", []),
        project_questions=prep_data.get("project_questions", []),
        role_specific_questions=prep_data.get("role_specific_questions", []),
    )
    updated_context = state.static_context.model_copy(update={"interview_prep": interview_prep})

    # Persist initial candidate, resume, and interview data into SQL Server
    thread_id = state.thread_id or (config.get("configurable", {}).get("thread_id") if config else None)
    if thread_id and state.static_context and state.static_context.resume_info:
        save_initial_interview(
            thread_id=thread_id,
            target_role=target_role,
            resume_pdf_path=state.resume_pdf_path,
            resume_text=state.resume_text or "",
            resume_info=state.static_context.resume_info,
            interview_prep=interview_prep,
            candidate_id=state.candidate_id,
        )

    return {"static_context": updated_context, "thread_id": thread_id}


def init_context_node(state: InterviewGraphState) -> dict:
    return {"static_context_str": build_static_context(state.static_context)}


def ask_question_node(state: InterviewGraphState, config: RunnableConfig = None) -> dict:
    result: NextQuestion = interview_agent(
        static_context=state.static_context_str,
        interview_state=state.interview_state,
        candidate_answer=state.candidate_answer,
    )

    updated_state = state.interview_state.model_copy(deep=True)

    if state.candidate_answer and updated_state.conversation:
        updated_state.conversation[-1].answer = state.candidate_answer
        updated_state.conversation[-1].score = result.score
        updated_state.total_score += result.score or 0
        updated_state.question_count += 1

    updated_state.conversation = updated_state.conversation + [ConversationTurn(question=result.question)]
    updated_state.status = "in_progress"

    # Sync ongoing turn progress to SQL Server
    thread_id = state.thread_id or (config.get("configurable", {}).get("thread_id") if config else None)
    if thread_id:
        update_interview_turn(thread_id, updated_state)

    return {"interview_state": updated_state, "candidate_answer": None}


def wait_for_answer_node(state: InterviewGraphState) -> dict:
    answer = interrupt({"question": state.interview_state.conversation[-1].question})
    return {"candidate_answer": answer}


def should_continue(state: InterviewGraphState) -> str:
    avg_score = (
        state.interview_state.total_score / state.interview_state.question_count
        if state.interview_state.question_count else None
    )
    if state.interview_state.question_count >= 15:
        return "end"
    if avg_score is not None and state.interview_state.question_count >= 3 and avg_score < 4:
        return "end"
    return "continue"


def end_node(state: InterviewGraphState) -> dict:
    updated_state = state.interview_state.model_copy(deep=True)
    updated_state.status = "completed"
    return {"interview_state": updated_state}


from interview_genie.database.db_conn import (
    save_initial_interview,
    update_interview_turn,
    save_completed_interview,
    get_prior_feedback_for_role,
    get_candidate_id_for_thread,
)


def evaluate_node(state: InterviewGraphState, config: RunnableConfig = None) -> dict:
    thread_id = state.thread_id or (config.get("configurable", {}).get("thread_id") if config else None)
    target_role = state.target_role or "Software Engineer"

    # Fetch candidate's previous feedback for the EXACT SAME target role (if any)
    historical_feedback = None
    candidate_id = state.candidate_id or (get_candidate_id_for_thread(thread_id) if thread_id else None)
    if candidate_id and thread_id:
        historical_feedback = get_prior_feedback_for_role(candidate_id, target_role, exclude_thread_id=thread_id)

    feedback = evaluate_interview(
        interview_state=state.interview_state,
        target_role=target_role,
        historical_feedback=historical_feedback,
    )

    if thread_id:
        save_completed_interview(thread_id, state.interview_state, feedback)

    return {"feedback": feedback}