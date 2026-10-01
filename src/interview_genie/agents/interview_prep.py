
import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

from interview_genie.Models.schema import InterviewPrepSchema

load_dotenv(find_dotenv(usecwd=True))


def generate_interview_prep(resume_info: dict, target_role: str) -> str:
    """Generate skill-wise (basic/intermediate/advanced) interview topics that the interview agent will ask the candidate."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        prompt = f"""
Target Role: {target_role}

Candidate Resume Info:
{resume_info}

Based on the candidate's skills, projects, and experience above, and the target role:
Identify the relevant technical skills and domains from the resume. For each skill, list the important interview topics and subtopics, categorized by difficulty level (basic, intermediate, advanced), that the interview agent should ask to the candidate during the interview.

Important instructions:
- Do NOT generate full interview questions. ONLY return the topics and subtopics for the interview agent to ask.
- Only include skills and topics actually relevant to the candidate's background and prioritized for the target role.
"""

        response = client.responses.parse(
            model="gpt-5.6-luna",
            input=[
                {"role": "system", "content": "You are an expert technical interviewer and career coach. You identify key topics for the interviewer agent to explore."},
                {"role": "user", "content": prompt},
            ],
            text_format=InterviewPrepSchema,
        )

        return response.output_parsed.model_dump_json(indent=2)

    except Exception as e:
        print(f"Error generating interview prep: {e}")
        return "{}"