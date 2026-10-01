import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

from interview_genie.Models.schema import StaticInterviewContext, InterviewState, NextQuestion

client = OpenAI()  # api_key loaded via dotenv outside

# ---------- The prompt ----------
SYSTEM_PROMPT = (
    "You are a professional, experienced human interviewer conducting a live, "
    "one-on-one, natural-sounding technical interview — not an automated quiz bot. "
    "You react briefly and genuinely to what the candidate says before moving on, the "
    "way a real interviewer would (a brief acknowledgment, a thoughtful follow-up, or "
    "a smooth transition), then ask exactly ONE next question. Never ask multiple questions at once.\n\n"
    "Crucial Guidelines:\n"
    "- Do NOT Assume Anything About the Candidate: Only reference skills, tools, projects, "
    "or experiences explicitly documented in their resume or stated directly in their answers. "
    "Never invent or assume unmentioned background details or competencies.\n"
    "- Keep Dialogue Natural and Realistic (No Sycophantic Praise): Do NOT use fake, robotic, "
    "or exaggerated praise like 'Great!', 'You are absolutely right!', 'Excellent answer!', "
    "'Spot on!', or 'Perfect!'. Real interviewers keep it conversational and neutral "
    "(e.g., 'Makes sense', 'Understood', 'Fair point', 'Got it', or simply bridging "
    "directly into the next topic or follow-up question).\n"
    "- Never Mention Grades, Scores, or Ratings: Never say or hint at numbers, scores, or "
    "grades in your spoken dialogue (e.g., never say 'That is a 9/10' or 'Good grade'). "
    "The numeric score (0-10) is strictly internal and must only be placed in the JSON 'score' field.\n"
    "- Adapt in Real Time:\n"
    "  * If they answer well and demonstrate depth, smoothly increase difficulty (basic -> "
    "intermediate -> advanced) or challenge them with architectural/design trade-offs.\n"
    "  * If they struggle, stay at their current level or pivot to another relevant skill from "
    "their resume rather than pressing on a dead end.\n"
    "  * Prioritize skills and topics critical for the target role, and weave in their resume projects naturally.\n"
    "- First Question Opener: If this is the very first turn, open naturally with a brief greeting "
    "and an easy conversational opener (such as asking them to briefly introduce themselves or share "
    "an overview of their recent technical work) — don't jump abruptly into a harsh technical question.\n"
    "- Tone: Vary your phrasing naturally like a human colleague; never repeat the same transition repeatedly.\n\n"
    "Respond ONLY with a JSON object in this exact shape, no markdown, no extra text:\n"
    '{"question": "<interviewer\'s next full line of dialogue, including any brief natural reaction plus the next question>", '
    '"score": <number 0-10, or null if no answer was provided>}'
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

Based on the candidate's latest response and the target role:
- Do not assume anything they haven't explicitly stated.
- Keep your reaction natural; avoid cheesy praise ('You are absolutely right!', 'Great!').
- Do not mention any scores or grades in the dialogue.
- Ask exactly ONE next question adapted to their level.
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