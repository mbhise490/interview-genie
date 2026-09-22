
import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

from interview_genie.Models.schema import InterviewPrepSchema

load_dotenv(find_dotenv(usecwd=True))


def generate_interview_prep(resume_info: dict, target_role: str) -> str:
    """Generate skill-wise (basic/intermediate/advanced) interview topics and project-based questions using the Responses API."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        prompt = f"""
Target Role: {target_role}

Candidate Resume Info:
{resume_info}

Based on the candidate's skills, projects, and experience above, and the target role:
1. For each relevant skill found in the resume, list important interview topics, each tagged as basic, intermediate, or advanced.
2. Generate interview questions specifically based on the candidate's projects.
3. Create scenario-based or role-specific interview questions tailored to the target role, derived from the candidate's resume and the target role requirements.
Only include skills actually present in the resume, prioritized by relevance to the target role.
"""

        response = client.responses.parse(
            model="gpt-5.6-luna",
            input=[
                {"role": "system", "content": "You are an expert technical interviewer and career coach."},
                {"role": "user", "content": prompt},
            ],
            text_format=InterviewPrepSchema,
        )

        return response.output_parsed.model_dump_json(indent=2)

    except Exception as e:
        print(f"Error generating interview prep: {e}")
        return "{}"