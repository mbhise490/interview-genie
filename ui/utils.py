import os
import time
import uuid
from typing import Optional


def get_uploads_dir() -> str:
    """Returns absolute path to uploads directory, ensuring it exists."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(base_dir, "uploads", "resumes")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_uploaded_resume(uploaded_file, candidate_id: Optional[str] = None) -> str:
    """Saves uploaded Streamlit file buffer into uploads/resumes and returns absolute file path."""
    upload_dir = get_uploads_dir()
    cid = candidate_id[:8] if candidate_id else "guest"
    ts = int(time.time())
    safe_name = os.path.basename(uploaded_file.name).replace(" ", "_")
    filename = f"{cid}_{ts}_{safe_name}"
    target_path = os.path.join(upload_dir, filename)

    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return os.path.abspath(target_path)


def generate_thread_id(prefix: str = "session") -> str:
    """Generates a unique session thread ID."""
    ts = int(time.time())
    rand_suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts}-{rand_suffix}"


def get_default_sample_resume_path() -> Optional[str]:
    """Returns absolute path to sample_resume.pdf if it exists in project root."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_path = os.path.join(base_dir, "sample_resume.pdf")
    if os.path.exists(sample_path):
        return os.path.abspath(sample_path)
    return None
