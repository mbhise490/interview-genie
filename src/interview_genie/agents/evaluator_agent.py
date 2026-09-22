import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

from interview_genie.Models.schema import InterviewState, InterviewFeedback

client = OpenAI()  # api_key loaded via dotenv outside

EVALUATOR_SYSTEM_PROMPT = (
    "You are an expert technical interviewer and hiring evaluator. You will "
    "be given a full interview transcript (questions, candidate answers, and "
    "per-answer scores) along with the target role the candidate was "
    "interviewing for. Analyze the entire conversation carefully and produce "
    "a structured evaluation.\n\n"
    "If previous feedback from a prior interview for the SAME target role is provided, "
    "you MUST compare their current performance against that past feedback. Specifically:\n"
    "- Check whether the candidate addressed previously identified weaknesses/improvement areas.\n"
    "- Note whether previous strengths were maintained.\n"
    "- Summarize their learning curve, growth trajectory, and progress in the 'historical_progress' field.\n"
    "- If no prior feedback was provided (e.g. first interview for this role), set 'historical_progress' to null.\n\n"
    "Be specific and evidence-based — every strength and improvement area "
    "must be grounded in something the candidate actually said, not generic "
    "advice. Reference the relevant skill/topic by name.\n\n"
    "Consider not just correctness but depth of understanding, clarity of "
    "communication, problem-solving approach, and how well their experience "
    "aligns with what the target role actually requires.\n\n"
    "Be honest and balanced — don't inflate strengths or soften weaknesses. "
    "The goal is genuinely useful feedback the candidate can act on.\n\n"
    "Respond ONLY with a JSON object matching this exact shape, no markdown, "
    "no extra text:\n"
    '{"target_role": "<role>", "overall_score": <0-10>, "overall_summary": '
    '"<summary>", "strong_areas": [{"area": "<area>", "reason": "<reason>"}], '
    '"improvement_areas": [{"area": "<area>", "reason": "<reason>", '
    '"suggestion": "<suggestion>"}], "role_fit_notes": "<notes>", '
    '"recommendation": "<strong_fit|moderate_fit|needs_improvement|not_a_fit>", '
    '"historical_progress": "<comparison with prior interview for same role, or null>"}'
)


def evaluate_interview(
    interview_state: InterviewState,
    target_role: str,
    historical_feedback: str = None,
) -> InterviewFeedback:
    """
    Analyzes the full interview transcript and target role, and returns
    structured feedback: strong areas, improvement areas, role-fit notes,
    an overall recommendation, and comparative progress if prior feedback
    exists for the same target role.
    """
    try:
        transcript = [t.model_dump() for t in interview_state.conversation]

        historical_note = ""
        if historical_feedback:
            historical_note = f"""
Candidate's Previous Feedback for this Same Target Role ({target_role}):
{historical_feedback}

Compare the candidate's current interview performance against their previous feedback for this exact role.
Assess whether previously identified improvement areas were addressed and summarize their growth trajectory in 'historical_progress'.
"""
        else:
            historical_note = "No previous feedback exists for this target role. Evaluate this interview as a standalone session and set 'historical_progress' to null."

        user_prompt = f"""
Target Role: {target_role}

{historical_note}

Full Interview Transcript:
{transcript}

Overall Total Score: {interview_state.total_score}
Total Questions Asked: {interview_state.question_count}

Analyze this transcript and produce the structured evaluation as instructed.
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=[
                {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.output_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[len("```json"):].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[len("```"):].strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-len("```")].strip()

        data = json.loads(raw_text)
        return InterviewFeedback(**data)

    except Exception as e:
        print(f"Error evaluating interview: {e}")
        return InterviewFeedback(
            target_role=target_role,
            overall_score=0.0,
            overall_summary="Evaluation failed.",
            strong_areas=[],
            improvement_areas=[],
            role_fit_notes="",
            recommendation="needs_improvement",
            historical_progress=None,
        )