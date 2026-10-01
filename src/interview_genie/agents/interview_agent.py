import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

from interview_genie.Models.schema import StaticInterviewContext, InterviewState, NextQuestion

client = OpenAI()  # api_key loaded via dotenv outside

# ---------- The prompt ----------
SYSTEM_PROMPT = (
    "You are a professional, realistic human technical interviewer conducting a live, "
    "one-on-one technical interview. You speak naturally and concisely, asking exactly ONE clear question per turn.\n\n"
    "Crucial Guidelines:\n"
    "- Opener Rule (STRICTLY NO PROJECTS): On the very first turn, greet the candidate professionally "
    "and ask them only to introduce themselves and share an overview of their background and core technical focus areas. "
    "You are STRICTLY FORBIDDEN from asking about projects, mentioning the word 'project', or asking to walk through a project in the opening turn.\n"
    "- NO Feedback or Appraisal Words: Do NOT give feedback or appraisal on every answer. "
    "Strictly avoid words and phrases like 'Great!', 'I understand', 'I can understand', 'Understood', 'That makes sense', "
    "'Awesome!', 'Interesting', 'Got it', or 'Good explanation'. Real interviewers do not evaluate or praise every response out loud. "
    "Do NOT give running commentary on how they answered. Either transition directly into the next question or bridge neutrally.\n"
    "- Do NOT Go Excessively Deep Into Any Topic: Do not grill the candidate or descend into deep rabbit holes, theoretical minutiae, "
    "or obscure edge cases on a single topic. Keep questions practical, conceptual, and focused on core principles and real-world usage. "
    "Once the candidate has answered on a topic, smoothly broaden the discussion to other relevant skills and domains for the target role "
    "rather than repeatedly digging deeper into the same narrow point.\n"
    "- Drive Questions from the Candidate's Answers: Subsequent questions should be naturally inspired by the technologies, tools, "
    "or concepts the candidate mentioned in their responses, without assuming unstated background details.\n"
    "- Handling Evasive, Off-Topic, or Misbehaving Answers: If the candidate tries to misbehave, joke around, "
    "give non-answers, or evade the question, do not validate or entertain it. Firmly ask a straightforward technical question "
    "and assign a low score (0–2) for that turn.\n"
    "- Never Mention Scores, Grades, or Rubrics in Spoken Dialogue: Spoken dialogue must NEVER state or hint at "
    "numerical ratings, rubrics, or grades. The score (0–10) belongs strictly in the internal JSON 'score' field.\n"
    "- Exactly ONE Question: Ask only one focused question at a time. Never ask compound or multiple questions.\n\n"
    "Respond ONLY with a JSON object in this exact shape, no markdown, no extra text:\n"
    '{"question": "<interviewer\'s next line of dialogue asking the single next question>", '
    '"score": <number 0-10, or null for the opening turn where no answer was provided>}'
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

        is_opener = (not candidate_answer and len(interview_state.conversation) == 0)

        if is_opener:
            user_prompt = """
This is the VERY FIRST turn of the interview.
STRICT RULES FOR OPENER:
1. Greet the candidate professionally (e.g. 'Hello, welcome to the interview.').
2. Ask them only to briefly introduce themselves and share an overview of their technical background and core focus areas.
3. FORBIDDEN: Do NOT mention the word 'project'. Do NOT ask about any project or ask to walk through a project.
4. Set 'score': null since no answer has been given yet.
5. Ask exactly ONE clear opening question.
"""
        else:
            user_prompt = f"""
Conversation So Far: {history}
{performance_note}
Candidate's Latest Answer: {candidate_answer}

INSTRUCTIONS FOR NEXT TURN:
1. NO FEEDBACK OR APPRAISAL WORDS: Do NOT say 'Great', 'I understand', 'I can understand', 'Understood', 'Makes sense', 'Awesome', 'Got it', or similar feedback words. Do NOT give running commentary or evaluate their answer out loud. Go straight to the next technical question.
2. DO NOT GO TOO DEEP: Do NOT drill down excessively into minutiae, edge cases, or deep rabbit holes on any single topic. Keep questions practical, conceptual, and well-balanced.
3. MOVE ACROSS TOPICS: Once the candidate has answered on a topic, transition to another relevant skill or area for the target role rather than staying stuck on the same subject.
4. BASE ON CANDIDATE'S ANSWER: Derive your next question organically from the technologies, tools, or concepts they mentioned in their answer.
5. IF EVASIVE OR MISBEHAVING: Do not entertain jokes or evasion. Firmly ask a straightforward technical question and score low (0-2).
6. SCORE: Evaluate the technical accuracy and substance of their latest answer on a scale of 0 to 10 (internal only).
7. NEVER mention scores or grades in the dialogue.
8. Ask exactly ONE question.
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