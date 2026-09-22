import os
import json
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")


class GenieAPIClient:
    """
    Hybrid client for Interview Genie.
    - If FastAPI backend is active, routes requests via HTTP REST API.
    - If FastAPI backend is offline (e.g. Streamlit Community Cloud), executes directly in Python.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_API_BASE_URL).rstrip("/")
        self._is_backend_online: Optional[bool] = None

    def _check_backend_online(self) -> bool:
        """Pings the FastAPI server to check if it is actively running."""
        try:
            r = requests.get(f"{self.base_url}/api/db/validate", timeout=1.5)
            self._is_backend_online = (r.status_code == 200)
            return self._is_backend_online
        except Exception:
            self._is_backend_online = False
            return False

    def is_api_online(self) -> bool:
        if self._is_backend_online is not None:
            return self._is_backend_online
        return self._check_backend_online()

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def validate_db(self) -> Dict[str, Any]:
        """Validates database connectivity and table readiness."""
        if self.is_api_online():
            try:
                res = requests.get(f"{self.base_url}/api/db/validate", timeout=5)
                if res.status_code == 200:
                    return res.json()
            except Exception:
                self._is_backend_online = False

        # In-process fallback (Streamlit Cloud mode)
        from interview_genie.database.db_conn import validate_db_connection
        return validate_db_connection()

    def register(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = "Candidate",
        phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registers a new candidate."""
        if not email or "@" not in email:
            raise ValueError("A valid email address is required.")
        if not password or len(password) < 4:
            raise ValueError("Password must be at least 4 characters.")

        if self.is_api_online():
            try:
                payload = {
                    "email": email.strip().lower(),
                    "password": password,
                    "full_name": (full_name or "Candidate").strip(),
                    "phone": phone.strip() if phone else None,
                }
                res = requests.post(f"{self.base_url}/api/auth/register", json=payload, timeout=15)
                if res.status_code == 200:
                    return res.json()
                err = res.json().get("detail", res.text)
                raise ValueError(err)
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        # In-process fallback
        from interview_genie.utils.auth import hash_password, create_access_token
        from interview_genie.database.db_conn import register_candidate_user
        pwd_hash = hash_password(password)
        candidate = register_candidate_user(
            email=email,
            password_hash=pwd_hash,
            full_name=full_name or "Candidate",
            phone=phone,
        )
        token = create_access_token({"sub": candidate["candidate_id"], "email": candidate["email"]})
        return {
            "access_token": token,
            "token_type": "bearer",
            "candidate_id": candidate["candidate_id"],
            "email": candidate["email"],
            "full_name": candidate["full_name"],
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Logs in a candidate and returns access token."""
        if self.is_api_online():
            try:
                payload = {
                    "email": email.strip().lower(),
                    "password": password,
                }
                res = requests.post(f"{self.base_url}/api/auth/login", json=payload, timeout=15)
                if res.status_code == 200:
                    return res.json()
                err = res.json().get("detail", "Invalid email or password.")
                raise ValueError(err)
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        # In-process fallback
        from interview_genie.utils.auth import verify_password, create_access_token
        from interview_genie.database.db_conn import get_candidate_by_email
        candidate = get_candidate_by_email(email)
        if not candidate or not candidate.get("password_hash"):
            raise ValueError("Invalid email or password.")
        if not verify_password(password, candidate["password_hash"]):
            raise ValueError("Invalid email or password.")
        token = create_access_token({"sub": candidate["candidate_id"], "email": candidate["email"]})
        return {
            "access_token": token,
            "token_type": "bearer",
            "candidate_id": candidate["candidate_id"],
            "email": candidate["email"],
            "full_name": candidate["full_name"],
        }

    def get_profile(self, token: str) -> Dict[str, Any]:
        """Retrieves candidate profile and complete interview history."""
        if self.is_api_online():
            try:
                headers = self._get_headers(token)
                res = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=15)
                if res.status_code == 200:
                    return res.json()
                err = res.json().get("detail", "Session expired or invalid token.")
                raise ValueError(err)
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        # In-process fallback
        from interview_genie.utils.auth import decode_access_token
        from interview_genie.database.db_conn import get_candidate_profile
        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            raise ValueError("Session expired or invalid token.")
        profile = get_candidate_profile(payload["sub"])
        if not profile:
            raise ValueError("Candidate profile not found.")
        return profile

    def start_interview(
        self,
        resume_pdf_path: str,
        target_role: str,
        thread_id: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Starts an interview session."""
        if self.is_api_online():
            try:
                headers = self._get_headers(token)
                payload = {
                    "resume_pdf_path": resume_pdf_path,
                    "target_role": target_role,
                    "thread_id": thread_id,
                }
                res = requests.post(f"{self.base_url}/api/interview/start", headers=headers, json=payload, timeout=180)
                if res.status_code == 200:
                    return res.json()
                err = res.json().get("detail", res.text)
                raise RuntimeError(f"Failed to start interview: {err}")
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        # In-process fallback (LangGraph direct invocation)
        from interview_genie.api.deps import interview_app
        from interview_genie.api.routes import _extract_turn_response
        from interview_genie.utils.auth import decode_access_token

        cand_id = None
        if token:
            payload = decode_access_token(token)
            if payload:
                cand_id = payload.get("sub")

        config = {"configurable": {"thread_id": thread_id}}
        result = interview_app.invoke(
            {
                "resume_pdf_path": resume_pdf_path,
                "target_role": target_role,
                "thread_id": thread_id,
                "candidate_id": cand_id,
            },
            config=config,
        )
        return _extract_turn_response(result).model_dump()

    def submit_answer(
        self,
        thread_id: str,
        answer: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submits candidate's answer and retrieves next turn."""
        if self.is_api_online():
            try:
                headers = self._get_headers(token)
                payload = {"thread_id": thread_id, "answer": answer}
                res = requests.post(f"{self.base_url}/api/interview/answer", headers=headers, json=payload, timeout=120)
                if res.status_code == 200:
                    return res.json()
                err = res.json().get("detail", res.text)
                raise RuntimeError(f"Failed to submit answer: {err}")
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        # In-process fallback
        from langgraph.types import Command
        from interview_genie.api.deps import interview_app
        from interview_genie.api.routes import _extract_turn_response

        config = {"configurable": {"thread_id": thread_id}}
        result = interview_app.invoke(Command(resume=answer), config=config)
        return _extract_turn_response(result).model_dump()

    def end_interview(
        self,
        thread_id: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ends interview session, generates comprehensive evaluation, and stores to DB."""
        if self.is_api_online():
            try:
                headers = self._get_headers(token)
                payload = {"thread_id": thread_id}
                res = requests.post(f"{self.base_url}/api/interview/end", headers=headers, json=payload, timeout=180)
                if res.status_code == 200:
                    return res.json()
                err = res.json().get("detail", res.text)
                raise RuntimeError(f"Failed to end interview: {err}")
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        # In-process fallback
        from interview_genie.api.deps import interview_app
        from interview_genie.api.routes import _extract_turn_response
        from interview_genie.database.db_conn import (
            get_candidate_id_for_thread,
            get_prior_feedback_for_role,
            save_completed_interview,
        )
        from interview_genie.agents.evaluator_agent import evaluate_interview
        from interview_genie.utils.auth import decode_access_token

        config = {"configurable": {"thread_id": thread_id}}
        state = interview_app.get_state(config)
        if not state or not state.values:
            raise RuntimeError("Interview session not found.")

        interview_state = state.values.get("interview_state")
        target_role = state.values.get("target_role", "Software Engineer")
        if not interview_state:
            raise RuntimeError("No active interview state found.")

        completed_state = interview_state.model_copy(deep=True)
        completed_state.status = "completed"

        cand_id = None
        if token:
            payload = decode_access_token(token)
            if payload:
                cand_id = payload.get("sub")
        if not cand_id:
            cand_id = get_candidate_id_for_thread(thread_id)

        prior_feedback = None
        if cand_id:
            prior_feedback = get_prior_feedback_for_role(cand_id, target_role, exclude_thread_id=thread_id)

        feedback = evaluate_interview(
            interview_state=completed_state,
            target_role=target_role,
            historical_feedback=prior_feedback,
        )
        save_completed_interview(thread_id, completed_state, feedback)
        interview_app.update_state(config, {"interview_state": completed_state, "feedback": feedback})
        return _extract_turn_response({"interview_state": completed_state, "feedback": feedback}).model_dump()

    def get_interview_status(self, thread_id: str) -> Dict[str, Any]:
        """Gets current interview status without advancing."""
        if self.is_api_online():
            try:
                res = requests.get(f"{self.base_url}/api/interview/{thread_id}/status", timeout=15)
                if res.status_code == 200:
                    return res.json()
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        from interview_genie.api.deps import interview_app
        from interview_genie.api.routes import _extract_turn_response
        config = {"configurable": {"thread_id": thread_id}}
        state = interview_app.get_state(config)
        values = dict(state.values) if state and state.values else {}
        if state and state.tasks:
            for task in state.tasks:
                if task.interrupts:
                    values["__interrupt__"] = list(task.interrupts)
                    break
        return _extract_turn_response(values).model_dump()

    def get_feedback(self, thread_id: str) -> Dict[str, Any]:
        """Gets final feedback for a completed interview."""
        if self.is_api_online():
            try:
                res = requests.get(f"{self.base_url}/api/interview/{thread_id}/feedback", timeout=15)
                if res.status_code == 200:
                    return res.json()
            except requests.exceptions.RequestException:
                self._is_backend_online = False

        from interview_genie.api.deps import interview_app
        config = {"configurable": {"thread_id": thread_id}}
        state = interview_app.get_state(config)
        feedback = state.values.get("feedback") if state and state.values else None
        if not feedback:
            raise RuntimeError("Feedback not yet available.")
        return feedback.model_dump() if hasattr(feedback, "model_dump") else feedback
