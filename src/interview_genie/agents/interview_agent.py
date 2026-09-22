import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

from interview_genie.Models.schema import StaticInterviewContext, InterviewState, NextQuestion

client = OpenAI()  # api_key loaded via dotenv outside

# ---------- The prompt ----------
SYSTEM_PROMPT = (
    "You are a warm, experienced human interviewer conducting a live, "
    "one-on-one, natural-sounding interview — not a quiz bot. You react "
    "briefly and genuinely to what the candidate says before moving on, the "
    "way a real interviewer would (a short acknowledgment, a follow-up, or "
    "a smooth transition), then ask exactly ONE next question. Never ask "
    "multiple questions at once.\n\n"
    "Adapt to the candidate in real time:\n"
    "- If they've been answering well, increase difficulty (move basic -> "
    "intermediate -> advanced) or move to a new, more challenging skill/topic.\n"
    "- If they've been struggling, stay at the same or an easier level, or "
    "switch to a different skill they might be stronger in, before giving up "
    "on a topic entirely.\n"
    "- Keep every question relevant to the target role — prioritize the "
    "skills and topics most important for that role over ones that are "
    "only tangentially relevant.\n"
    "- Weave in project-based questions naturally when appropriate, not as "
    "a separate disconnected section.\n\n"
    "If the candidate just answered, first score that answer 0-10 based on "
    "correctness, depth, and clarity — but never say the score out loud to "
    "the candidate.\n\n"
    "If this is the very first question, open naturally (e.g. a brief "
    "greeting and an easy opener like asking them to tell you about "
    "themselves) — don't jump straight into a technical question.\n\n"
    "Vary phrasing and tone like a real person would — don't repeat the "
    "same transition every time.\n\n"
    "Respond ONLY with a JSON object in this exact shape, no markdown, no "
    "extra text:\n"
    '{"question": "<interviewer\'s next full line of dialogue, including '
    'any brief reaction plus the next question>", "score": <number 0-10, '
    "or null if no answer was provided>}"
)


def build_static_context(context: StaticInterviewContext) -> str:
    """Builds the full system prompt once — SYSTEM_PROMPT + target role + resume + prep. Fixed for the whole session."""
    return f"""{SYSTEM_PROMPT}

Target Role: {context.target_role}
Resume Info: {context.resume_info.model_dump()}
Interview Prep Topics: {context.interview_prep.model_dump()}
"""


# ---------- The agent ----------
def interview_agent(
    static_context: str,
    interview_state: InterviewState,
    candidate_answer: str = None,
) -> NextQuestion:
    """
    Runs one turn of a one-on-one interview. static_context (built once by
    build_static_context) is passed unchanged every turn. Only the
    conversation history and candidate_answer change per call.
    """
    try:
        history = [t.model_dump() for t in interview_state.conversation]

        recent_scores = [t.score for t in interview_state.conversation if t.score is not None]
        performance_note = f"Recent scores: {recent_scores}" if recent_scores else "No answers scored yet."

        user_prompt = f"""
Conversation So Far: {history}
{performance_note}
Candidate's Latest Answer: {candidate_answer}

Based on the candidate's performance trend above and the target role, decide
the right next question — adjust difficulty and topic accordingly, and ask
only ONE question.
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=[
                {"role": "system", "content": static_context},
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
        return NextQuestion(**data)

    except Exception as e:
        print(f"Error running interview agent: {e}")
        return NextQuestion(question="", score=None)