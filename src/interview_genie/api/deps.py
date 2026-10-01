from typing import Optional
from fastapi import Header, Query, HTTPException, status

from interview_genie.graph.build_graph import build_interview_graph
from interview_genie.database.db_conn import get_candidate_profile

# Single compiled graph instance, reused across requests
interview_app = build_interview_graph()


def get_current_user(
    x_candidate_id: Optional[str] = Header(None, alias="X-Candidate-ID"),
    candidate_id: Optional[str] = Query(None),
) -> dict:
    """
    Dependency that enforces basic candidate authentication.
    Identifies candidate by candidate_id (passed via X-Candidate-ID header or query param).
    Returns candidate profile dict or raises HTTP 401.
    """
    cid = x_candidate_id or candidate_id
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide your candidate_id via X-Candidate-ID header or query param.",
        )

    profile = get_candidate_profile(cid)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Candidate account not found.",
        )

    return profile


def get_optional_current_user(
    x_candidate_id: Optional[str] = Header(None, alias="X-Candidate-ID"),
    candidate_id: Optional[str] = Query(None),
) -> Optional[dict]:
    """
    Dependency that returns candidate profile if a valid candidate_id is present, or None if anonymous.
    """
    cid = x_candidate_id or candidate_id
    if not cid:
        return None

    try:
        return get_candidate_profile(cid)
    except Exception:
        return None