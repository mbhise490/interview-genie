from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from interview_genie.graph.build_graph import build_interview_graph
from interview_genie.utils.auth import decode_access_token
from interview_genie.database.db_conn import get_candidate_profile

# Single compiled graph instance, reused across requests
interview_app = build_interview_graph()

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Dependency that enforces JWT authentication.
    Returns candidate profile dict or raises HTTP 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    candidate_id = payload.get("sub") or payload.get("candidate_id")
    if not candidate_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile = get_candidate_profile(candidate_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Candidate account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return profile


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Dependency that returns candidate profile if a valid JWT is present, or None if anonymous.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            return None
        candidate_id = payload.get("sub") or payload.get("candidate_id")
        if not candidate_id:
            return None
        return get_candidate_profile(candidate_id)
    except Exception:
        return None