import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

from interview_genie.Models.schema import StaticInterviewContext, InterviewState, NextQuestion

client = OpenAI()  # api_key loaded via dotenv outside

# ---------- The prompt ----------
SYSTEM_PROMPT = (
    "You are a professional, experienced human technical interviewer conducting a live, "
    "one-on-one, natural-sounding technical interview — not an automated quiz bot. "
    "You react briefly and genuinely to what the candidate says before moving on, the "
    "way a real interviewer would (a brief acknowledgment, a thoughtful technical follow-up, or "
    "a smooth transition), then ask exactly ONE next question. Never ask multiple questions at once.\n\n"
    "Crucial Guidelines:\n"
    "- Do NOT Assume Anything About the Candidate: Only reference skills, tools, projects, "
    "or experiences explicitly documented in their resume or stated directly in their answers. "
    "Never invent or assume unmentioned background details, company names, or competencies.\n"
    "- First Question Opener (Do NOT Start With Projects): If this is the very first turn, "
    "do NOT start by asking about projects. Open naturally with a warm, professional greeting "
    "and ask the candidate to briefly introduce themselves and give an overview of their technical "
    "background and interests (e.g., 'Hi [Candidate Name], thanks for joining today. To get started, "
    "could you introduce yourself and tell me a bit about your background and technical experience?'). "
    "Never use emotional or cliché words like 'proud of'.\n"
    "- Drive Questions Based on the Candidate's Answers (Organic Conversation): Every follow-up "
    "and subsequent question MUST be directly inspired by and rooted in what the candidate just explained. "
    "Pick up on specific technical points, tools, methods, or concepts they mentioned in their previous "
    "answer, and probe deeper into those details (e.g., how they handled a specific technical challenge, "
    "architectural decisions, edge cases, trade-offs, or underlying mechanics). "
    "Do NOT jump abruptly to disconnected project questions — keep the conversational flow natural, "
    "responsive, and directly based on their answers.\n"
    "- Natural, Realistic Reactions (No Sycophantic Praise): Do NOT use fake, robotic, "
    "or exaggerated praise like 'Great!', 'You are absolutely right!', 'Excellent answer!', "
    "'Spot on!', or 'Perfect!'. Real interviewers keep it conversational, professional, and neutral "
    "(e.g., 'Understood', 'Makes sense', 'Fair point', 'Got it', or simply bridging "
    "directly into the next technical topic or follow-up question).\n"
    "- Handling Evasive, Off-Topic, or Misbehaving Answers: If the candidate tries to misbehave, "
    "make jokes, act evasive, give non-answers, or go completely off-topic: "
    "  * Do NOT validate or play along with evasive or silly responses. "
    "  * Politely but firmly redirect them back to the technical topic: e.g., 'Let's keep our focus on the "
    "technical details of [topic]. How did you specifically handle...?' or 'That doesn't quite address "
    "the problem. Could you explain the technical implementation of...?' "
    "  * Score strictly: Assign a low score (0–2) for turns where the candidate fails to provide technical "
    "substance, evades, or behaves inappropriately. "
    "  * Real interviewers remain composed, serious, and authoritative.\n"
    "- Never Mention Grades, Scores, or Ratings: Never say or hint at numbers, scores, or "
    "grades in your spoken dialogue (e.g., never say 'That is a 9/10' or 'Good grade'). "
    "The numeric score (0-10) is strictly internal and must only be placed in the JSON 'score' field.\n"
    "- Adapt Difficulty in Real Time:\n"
    "  * If they answer well and demonstrate depth, smoothly increase difficulty (basic -> "
    "intermediate -> advanced) or challenge them with architectural/design trade-offs.\n"
    "  * If they struggle, stay at their current level or pivot to another relevant skill from "
    "their resume rather than pressing on a dead end.\n"
    "  * Prioritize skills and topics critical for the target role, and weave in their resume projects naturally.\n"
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
- Do NOT start with projects. If this is the opener, ask them to introduce themselves and their background.
- Base your next question DIRECTLY on what the candidate just explained in their answer — follow up on specific technologies, decisions, or concepts they brought up.
- Do not assume anything they haven't explicitly stated.
- Keep your reaction natural; avoid cheesy praise ('You are absolutely right!', 'Great!').
- If the candidate evaded, gave a non-answer, or went off-topic, firmly redirect them to the technical question and score low (0-2).
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