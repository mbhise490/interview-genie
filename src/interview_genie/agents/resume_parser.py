import os
import sys
from pathlib import Path
from openai import OpenAI
from pypdf import PdfReader
import pdfplumber
from dotenv import load_dotenv, find_dotenv

from interview_genie.Models.schema import ResumeInfo

load_dotenv(find_dotenv(usecwd=True))


def extract_resume_text(pdf_path: str) -> str:
    """Extract text from a PDF resume file. Never raises, returns '' on any failure."""
    try:
        if not pdf_path or not isinstance(pdf_path, str):
            print(f"Invalid path provided: {pdf_path!r}")
            return ""

        if not os.path.isfile(pdf_path):
            print(f"File not found: {pdf_path}")
            return ""

        if not pdf_path.lower().endswith(".pdf"):
            print(f"Not a PDF file: {pdf_path}")
            return ""

        text = ""
        # Primary: try pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_err:
                        print(f"Failed to extract text from page {page_num} with pdfplumber: {page_err}")
                        continue
        except Exception as plumber_err:
            print(f"pdfplumber failed on {pdf_path}: {plumber_err}, falling back to pypdf")

        # Fallback: if text is still empty, try pypdf
        if not text.strip():
            try:
                reader = PdfReader(pdf_path)
                for page_num, page in enumerate(reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_err:
                        print(f"Failed to extract text from page {page_num} with pypdf: {page_err}")
                        continue
            except Exception as pypdf_err:
                print(f"Error reading PDF with pypdf: {pypdf_err}")

        if not text.strip():
            print(f"No text could be extracted from: {pdf_path}")
            return ""

        return text.strip()

    except Exception as e:
        print(f"Unexpected error reading PDF {pdf_path}: {e}")
        return ""


def parse_resume_with_llm(resume_text: str) -> str:
    """Send resume text to GPT and return structured JSON matching ResumeInfo."""
    try:
        if not resume_text or not isinstance(resume_text, str) or not resume_text.strip():
            print("No resume text provided for parsing.")
            return "{}"

        api_key = os.environ.get("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured information from the resume text into the given schema. "
                        "Note dont include any extra information or explanations, only provide the structured JSON output."
                    ),
                },
                {"role": "user", "content": resume_text},
            ],
            response_format=ResumeInfo,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            return "{}"
        return parsed.model_dump_json(indent=2)

    except Exception as e:
        print(f"Error parsing resume with LLM: {e}")
        return "{}"



