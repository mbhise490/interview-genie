from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session

from interview_genie_v2.database.db_conn import get_session
from interview_genie_v2.database.models import User
from interview_genie_v2.database.repositories import get_user_by_email
from interview_genie_v2.utils.auth import DUMMY_HASH, verify_password

security = HTTPBasic()

def get_current_user(credentials: Annotated[HTTPBasicCredentials, Depends(security)],session: Annotated[Session, Depends(get_session)],) -> User:
    user = get_user_by_email(session, credentials.username)
    password_ok = verify_password(credentials.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Basic"},)
    return user