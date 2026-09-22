import os
import re
import json
from typing import Optional, Tuple, List
import pyodbc
from dotenv import load_dotenv, find_dotenv

from interview_genie.Models.schema import ResumeInfo, InterviewPrep, InterviewState, InterviewFeedback
from interview_genie.database import sqlite_conn

load_dotenv(find_dotenv(usecwd=True))

_sql_server_available_cache: Optional[bool] = None


def is_sql_server_available() -> bool:
    """Checks whether Microsoft SQL Server is reachable. Caches result for performance."""
    global _sql_server_available_cache
    if _sql_server_available_cache is not None:
        return _sql_server_available_cache

    if os.getenv("USE_SQLITE", "false").lower() in ("true", "1", "yes"):
        print("[DB] USE_SQLITE is set. Using self-contained SQLite database.")
        _sql_server_available_cache = False
        return False

    try:
        conn = get_db_connection()
        conn.close()
        _sql_server_available_cache = True
        return True
    except Exception as e:
        print(f"[DB] SQL Server unreachable ({e}). Automatically falling back to self-contained SQLite.")
        _sql_server_available_cache = False
        return False


def get_connection_string() -> str:
    """Builds the ODBC connection string for SQL Server."""
    server = os.environ.get("SQL_SERVER", r"localhost\SQLEXPRESS")
    database = os.environ.get("SQL_DATABASE", "InterviewGenie")
    # If set to master, override to InterviewGenie where the tables live
    if database.lower() == "master":
        database = "InterviewGenie"
    driver = os.environ.get("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    trusted = os.environ.get("SQL_TRUSTED_CONNECTION", "yes")
    trust_cert = os.environ.get("SQL_TRUST_SERVER_CERTIFICATE", "yes")

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Trusted_Connection={trusted};"
        f"TrustServerCertificate={trust_cert}"
    )


def get_db_connection() -> pyodbc.Connection:
    """Returns an active pyodbc connection to the database."""
    conn_str = get_connection_string()
    return pyodbc.connect(conn_str, timeout=5)


def ensure_auth_schema() -> None:
    """Ensures candidates table has password_hash column for authentication."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('candidates') AND name = 'password_hash'
            )
            BEGIN
                ALTER TABLE candidates ADD password_hash NVARCHAR(255) NULL;
            END
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB WARNING] ensure_auth_schema check failed: {e}")


def validate_db_connection() -> dict:
    """
    Validates that the database connection works and required tables exist.
    Returns status info including SQL Server version and table row counts.
    Falls back to SQLite if SQL Server is not reachable.
    """
    if not is_sql_server_available():
        return sqlite_conn.validate_sqlite_db()

    try:
        ensure_auth_schema()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version_row = cursor.fetchone()
        version = version_row[0] if version_row else "Unknown"

        tables_info = {}
        for table in ["candidates", "resume_info", "interview"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                tables_info[table] = cursor.fetchone()[0]
            except Exception as table_err:
                tables_info[table] = f"Error: {table_err}"

        conn.close()
        return {
            "status": "connected",
            "server_version": version.split("\n")[0].strip(),
            "database": os.environ.get("SQL_DATABASE", "InterviewGenie"),
            "tables": tables_info,
        }
    except Exception as e:
        return sqlite_conn.validate_sqlite_db()


# =========================================================================
# Authentication & User Management
# =========================================================================

def register_candidate_user(
    email: str,
    password_hash: str,
    full_name: str = "Candidate",
    phone: Optional[str] = None,
) -> dict:
    """
    Registers a new candidate with email and hashed password.
    If candidate already exists without a password (from prior resume upload),
    updates their record with credentials.
    """
    if not is_sql_server_available():
        return sqlite_conn.register_candidate_user(email, password_hash, full_name, phone)

    normalized_email = email.strip().lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT candidate_id, password_hash, full_name, phone FROM candidates WHERE email = ?",
            (normalized_email,),
        )
        existing = cursor.fetchone()

        if existing:
            cand_id, existing_hash, existing_name, existing_phone = existing
            if existing_hash:
                raise ValueError("An account with this email already exists. Please log in.")
            # Upgrade existing candidate with credentials
            cursor.execute(
                """
                UPDATE candidates
                SET password_hash = ?,
                    full_name = COALESCE(NULLIF(?, 'Candidate'), full_name),
                    phone = COALESCE(?, phone)
                WHERE candidate_id = ?
                """,
                (password_hash, full_name, phone, cand_id),
            )
            candidate_id = cand_id
            name = full_name if full_name != "Candidate" else existing_name
            ph = phone or existing_phone
        else:
            cursor.execute(
                """
                INSERT INTO candidates (full_name, email, phone, password_hash)
                OUTPUT INSERTED.candidate_id
                VALUES (?, ?, ?, ?)
                """,
                (full_name, normalized_email, phone, password_hash),
            )
            candidate_id = cursor.fetchone()[0]
            name = full_name
            ph = phone

        conn.commit()
        return {
            "candidate_id": str(candidate_id),
            "email": normalized_email,
            "full_name": name,
            "phone": ph,
        }
    finally:
        conn.close()


def get_candidate_by_email(email: str) -> Optional[dict]:
    """Retrieves candidate credentials and profile by email for login."""
    if not is_sql_server_available():
        return sqlite_conn.get_candidate_by_email(email)

    normalized_email = email.strip().lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT candidate_id, full_name, email, phone, password_hash, created_at
            FROM candidates
            WHERE email = ?
            """,
            (normalized_email,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "candidate_id": str(row[0]),
            "full_name": row[1],
            "email": row[2],
            "phone": row[3],
            "password_hash": row[4],
            "created_at": str(row[5]) if row[5] else None,
        }
    finally:
        conn.close()


def get_candidate_profile(candidate_id: str) -> Optional[dict]:
    """Retrieves candidate profile and complete list of interview history."""
    if not is_sql_server_available():
        return sqlite_conn.get_candidate_profile(candidate_id)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT candidate_id, full_name, email, phone, created_at
            FROM candidates
            WHERE candidate_id = ?
            """,
            (candidate_id,),
        )
        cand_row = cursor.fetchone()
        if not cand_row:
            return None

        # Fetch candidate's interviews
        cursor.execute(
            """
            SELECT interview_id, thread_id, target_role, status, total_score,
                   question_count, started_at, completed_at, interview_feed_back
            FROM interview
            WHERE candidate_id = ?
            ORDER BY created_at DESC
            """,
            (candidate_id,),
        )
        interviews = []
        for r in cursor.fetchall():
            fb_summary = None
            recommendation = None
            if r[8]:
                try:
                    fb_data = json.loads(r[8])
                    fb_summary = fb_data.get("overall_summary")
                    recommendation = fb_data.get("recommendation")
                except Exception:
                    pass

            interviews.append({
                "interview_id": str(r[0]),
                "thread_id": r[1],
                "target_role": r[2],
                "status": r[3],
                "total_score": float(r[4]),
                "question_count": r[5],
                "started_at": str(r[6]) if r[6] else None,
                "completed_at": str(r[7]) if r[7] else None,
                "overall_summary": fb_summary,
                "recommendation": recommendation,
            })

        return {
            "candidate_id": str(cand_row[0]),
            "full_name": cand_row[1],
            "email": cand_row[2],
            "phone": cand_row[3],
            "created_at": str(cand_row[4]) if cand_row[4] else None,
            "interviews": interviews,
        }
    finally:
        conn.close()


# =========================================================================
# Historical Role-Specific Feedback Retrieval
# =========================================================================

def get_prior_feedback_for_role(
    candidate_id: str,
    target_role: str,
    exclude_thread_id: Optional[str] = None,
) -> Optional[str]:
    """
    Looks up the candidate's latest completed interview feedback for the EXACT SAME target role.
    Returns the raw feedback JSON string if found, otherwise None.
    """
    if not candidate_id or not target_role:
        return None

    if not is_sql_server_available():
        return sqlite_conn.get_prior_feedback_for_role(candidate_id, target_role, exclude_thread_id)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT TOP 1 interview_feed_back
            FROM interview
            WHERE candidate_id = ?
              AND target_role = ?
              AND status = 'completed'
              AND interview_feed_back IS NOT NULL
        """
        params = [candidate_id, target_role]
        if exclude_thread_id:
            query += " AND thread_id != ?"
            params.append(exclude_thread_id)

        query += " ORDER BY completed_at DESC"

        cursor.execute(query, tuple(params))
        row = cursor.fetchone()
        if row and row[0]:
            print(f"[DB] Found prior feedback for candidate={candidate_id}, target_role='{target_role}'")
            return row[0]
        return None
    except Exception as e:
        print(f"[DB ERROR] Error retrieving prior feedback for role: {e}")
        return None
    finally:
        conn.close()


def get_candidate_id_for_thread(thread_id: str) -> Optional[str]:
    """Retrieves candidate_id associated with a thread_id."""
    if not thread_id:
        return None

    if not is_sql_server_available():
        return sqlite_conn.get_candidate_id_for_thread(thread_id)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT candidate_id FROM interview WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()
        return str(row[0]) if row else None
    except Exception as e:
        print(f"[DB ERROR] Error looking up candidate for thread {thread_id}: {e}")
        return None
    finally:
        conn.close()


# =========================================================================
# Resume & Interview Session Persistence
# =========================================================================

def extract_candidate_details(candidate_info: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Extracts (full_name, email, phone) from resume candidate_info text.
    """
    if not candidate_info:
        return "Candidate", None, None

    # Extract email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", candidate_info)
    email = email_match.group(0).lower() if email_match else None

    # Extract phone
    phone_match = re.search(r"\(?\+?[0-9]{1,4}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}", candidate_info)
    phone = phone_match.group(0).strip() if phone_match else None

    # Extract name (typically the first non-empty line or before contact info)
    lines = [line.strip() for line in candidate_info.splitlines() if line.strip()]
    full_name = "Candidate"
    if lines:
        first_line = lines[0]
        first_line = re.sub(r"^(Candidate\s*Info\s*:|Name\s*:|Candidate\s*:)", "", first_line, flags=re.IGNORECASE).strip()
        if "|" in first_line:
            first_line = first_line.split("|")[0].strip()
        if "@" in first_line:
            first_line = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "", first_line).strip()
        if first_line:
            full_name = first_line[:255]

    return full_name, email, phone


def save_initial_interview(
    thread_id: str,
    target_role: str,
    resume_pdf_path: Optional[str],
    resume_text: str,
    resume_info: ResumeInfo,
    interview_prep: InterviewPrep,
    candidate_id: Optional[str] = None,
) -> dict:
    """
    Stores candidate, resume, and initial interview metadata into the database.
    If candidate_id is passed (e.g. authenticated user), it is used directly.
    Otherwise, checks email or creates a new candidate.
    """
    if not is_sql_server_available():
        return sqlite_conn.save_initial_interview(
            thread_id=thread_id,
            target_role=target_role,
            resume_pdf_path=resume_pdf_path,
            resume_text=resume_text,
            resume_info=resume_info,
            interview_prep=interview_prep,
            candidate_id=candidate_id,
        )

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Candidate extraction & insertion / retrieval
        if not candidate_id:
            full_name, email, phone = extract_candidate_details(resume_info.candidate_info)

            if email:
                cursor.execute("SELECT candidate_id FROM candidates WHERE email = ?", (email,))
                row = cursor.fetchone()
                if row:
                    candidate_id = row[0]

            if not candidate_id:
                cursor.execute(
                    """
                    INSERT INTO candidates (full_name, email, phone)
                    OUTPUT INSERTED.candidate_id
                    VALUES (?, ?, ?)
                    """,
                    (full_name, email, phone),
                )
                candidate_id = cursor.fetchone()[0]

        # 2. Insert Resume Info
        resume_parsed_json = resume_info.model_dump_json()
        cursor.execute(
            """
            INSERT INTO resume_info (candidate_id, resume_pdf_path, resume_text, resume_parsed)
            OUTPUT INSERTED.resume_id
            VALUES (?, ?, ?, ?)
            """,
            (candidate_id, resume_pdf_path or "", resume_text or "", resume_parsed_json),
        )
        resume_id = cursor.fetchone()[0]

        # 3. Insert or Update Interview record
        prep_json = interview_prep.model_dump_json()

        cursor.execute("SELECT interview_id FROM interview WHERE thread_id = ?", (thread_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE interview
                SET candidate_id = ?,
                    resume_id = ?,
                    target_role = ?,
                    interview_prep_topic = ?,
                    status = 'in_progress',
                    started_at = SYSUTCDATETIME()
                WHERE thread_id = ?
                """,
                (candidate_id, resume_id, target_role, prep_json, thread_id),
            )
            interview_id = existing[0]
        else:
            cursor.execute(
                """
                INSERT INTO interview (candidate_id, resume_id, thread_id, target_role, interview_prep_topic, status, started_at)
                OUTPUT INSERTED.interview_id
                VALUES (?, ?, ?, ?, ?, 'in_progress', SYSUTCDATETIME())
                """,
                (candidate_id, resume_id, thread_id, target_role, prep_json),
            )
            interview_id = cursor.fetchone()[0]

        conn.commit()
        print(f"[DB] Saved initial interview session: thread_id={thread_id}, candidate_id={candidate_id}")
        return {
            "candidate_id": str(candidate_id),
            "resume_id": str(resume_id),
            "interview_id": str(interview_id),
        }

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] Failed to save initial interview: {e}")
        return {}
    finally:
        if conn:
            conn.close()


def update_interview_turn(thread_id: str, interview_state: InterviewState) -> bool:
    """
    Updates the ongoing transcript, question count, and total score in the database.
    """
    if not thread_id:
        return False

    if not is_sql_server_available():
        return sqlite_conn.update_interview_turn(thread_id, interview_state)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        script_json = json.dumps([t.model_dump() for t in interview_state.conversation])
        total_score = float(interview_state.total_score)
        question_count = int(interview_state.question_count)
        status = interview_state.status

        cursor.execute(
            """
            UPDATE interview
            SET interview_script = ?,
                total_score = ?,
                question_count = ?,
                status = ?
            WHERE thread_id = ?
            """,
            (script_json, total_score, question_count, status, thread_id),
        )
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] Failed to update interview turn: {e}")
        return False
    finally:
        if conn:
            conn.close()


def save_completed_interview(
    thread_id: str,
    interview_state: InterviewState,
    feedback: Optional[InterviewFeedback] = None,
) -> bool:
    """
    Marks the interview as completed and saves the full transcript, final scores,
    and structured feedback into the database.
    """
    if not thread_id:
        return False

    if not is_sql_server_available():
        return sqlite_conn.save_completed_interview(thread_id, interview_state, feedback)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        script_json = json.dumps([t.model_dump() for t in interview_state.conversation])
        total_score = float(interview_state.total_score)
        question_count = int(interview_state.question_count)
        feedback_json = feedback.model_dump_json() if feedback else None

        cursor.execute(
            """
            UPDATE interview
            SET status = 'completed',
                interview_script = ?,
                total_score = ?,
                question_count = ?,
                interview_feed_back = ?,
                completed_at = SYSUTCDATETIME()
            WHERE thread_id = ?
            """,
            (script_json, total_score, question_count, feedback_json, thread_id),
        )
        conn.commit()
        print(f"[DB] Successfully stored completed interview for thread_id={thread_id}")
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] Failed to save completed interview: {e}")
        return False
    finally:
        if conn:
            conn.close()
