import os
import json
import sqlite3
import uuid
import datetime
from typing import Optional, Dict, Any, Tuple
from interview_genie.Models.schema import ResumeInfo, InterviewPrep, InterviewState, InterviewFeedback

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "interview_genie.db"))


def get_sqlite_conn() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    """Initializes tables and indices in SQLite if they don't already exist."""
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_info (
                resume_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                resume_pdf_path TEXT,
                resume_text TEXT,
                resume_parsed TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview (
                interview_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                resume_id TEXT NOT NULL,
                thread_id TEXT UNIQUE NOT NULL,
                target_role TEXT NOT NULL,
                interview_prep_topic TEXT,
                interview_script TEXT,
                interview_feed_back TEXT,
                status TEXT DEFAULT 'in_progress',
                total_score REAL DEFAULT 0.0,
                question_count INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id),
                FOREIGN KEY (resume_id) REFERENCES resume_info(resume_id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Auto-initialize SQLite on import
try:
    init_sqlite_db()
except Exception as _e:
    pass


def validate_sqlite_db() -> Dict[str, Any]:
    """Validates SQLite table readiness and returns status."""
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        counts = {}
        for tbl in ["candidates", "resume_info", "interview"]:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            counts[tbl] = cursor.fetchone()[0]
        conn.close()
        return {
            "status": "connected",
            "server_version": f"SQLite {sqlite3.sqlite_version} (Self-Contained Cloud Engine)",
            "database": os.path.basename(SQLITE_DB_PATH),
            "tables": counts,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def register_candidate_user(
    email: str,
    password_hash: str,
    full_name: str = "Candidate",
    phone: Optional[str] = None,
) -> dict:
    """Registers candidate in SQLite or updates credentials."""
    init_sqlite_db()
    conn = get_sqlite_conn()
    normalized_email = email.strip().lower()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT candidate_id, password_hash FROM candidates WHERE email = ?", (normalized_email,))
        existing = cursor.fetchone()

        if existing:
            if existing["password_hash"]:
                raise ValueError("An account with this email address already exists. Please sign in.")
            cid = existing["candidate_id"]
            cursor.execute(
                """
                UPDATE candidates
                SET password_hash = ?, full_name = COALESCE(?, full_name), phone = COALESCE(?, phone)
                WHERE candidate_id = ?
                """,
                (password_hash, full_name, phone, cid),
            )
        else:
            cid = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO candidates (candidate_id, full_name, email, phone, password_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cid, full_name.strip(), normalized_email, phone, password_hash),
            )

        conn.commit()
        return {
            "candidate_id": cid,
            "email": normalized_email,
            "full_name": full_name,
            "phone": phone,
        }
    finally:
        conn.close()


def get_candidate_by_email(email: str) -> Optional[dict]:
    """Retrieves candidate credentials by email."""
    init_sqlite_db()
    conn = get_sqlite_conn()
    normalized_email = email.strip().lower()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT candidate_id, full_name, email, phone, password_hash, created_at FROM candidates WHERE email = ?",
            (normalized_email,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def get_candidate_profile(candidate_id: str) -> Optional[dict]:
    """Retrieves candidate profile and all interview history from SQLite."""
    init_sqlite_db()
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT candidate_id, full_name, email, phone, created_at FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        )
        cand_row = cursor.fetchone()
        if not cand_row:
            return None

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
            if r["interview_feed_back"]:
                try:
                    fb_data = json.loads(r["interview_feed_back"])
                    fb_summary = fb_data.get("overall_summary")
                    recommendation = fb_data.get("recommendation")
                except Exception:
                    pass

            interviews.append({
                "interview_id": r["interview_id"],
                "thread_id": r["thread_id"],
                "target_role": r["target_role"],
                "status": r["status"],
                "total_score": float(r["total_score"]),
                "question_count": r["question_count"],
                "started_at": str(r["started_at"]) if r["started_at"] else None,
                "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
                "overall_summary": fb_summary,
                "recommendation": recommendation,
            })

        return {
            "candidate_id": cand_row["candidate_id"],
            "full_name": cand_row["full_name"],
            "email": cand_row["email"],
            "phone": cand_row["phone"],
            "created_at": str(cand_row["created_at"]) if cand_row["created_at"] else None,
            "interviews": interviews,
        }
    finally:
        conn.close()


def get_prior_feedback_for_role(
    candidate_id: str,
    target_role: str,
    exclude_thread_id: Optional[str] = None,
) -> Optional[str]:
    """Retrieves candidate's latest completed interview feedback for the EXACT SAME target role."""
    if not candidate_id or not target_role:
        return None

    init_sqlite_db()
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()
        query = """
            SELECT interview_feed_back
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

        query += " ORDER BY completed_at DESC LIMIT 1"
        cursor.execute(query, tuple(params))
        row = cursor.fetchone()
        if row and row["interview_feed_back"]:
            print(f"[SQLite] Found prior feedback for candidate={candidate_id}, target_role='{target_role}'")
            return row["interview_feed_back"]
        return None
    except Exception as e:
        print(f"[SQLite ERROR] Error retrieving prior feedback: {e}")
        return None
    finally:
        conn.close()


def get_candidate_id_for_thread(thread_id: str) -> Optional[str]:
    """Retrieves candidate_id for a given thread_id."""
    if not thread_id:
        return None
    init_sqlite_db()
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT candidate_id FROM interview WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()
        return row["candidate_id"] if row else None
    finally:
        conn.close()


def save_initial_interview(
    thread_id: str,
    target_role: str,
    resume_pdf_path: Optional[str],
    resume_text: str,
    resume_info: ResumeInfo,
    interview_prep: InterviewPrep,
    candidate_id: Optional[str] = None,
) -> dict:
    """Stores candidate, resume, and initial interview metadata into SQLite."""
    init_sqlite_db()
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()

        # 1. Candidate extraction if not passed
        if not candidate_id:
            from interview_genie.database.db_conn import extract_candidate_details
            full_name, email, phone = extract_candidate_details(resume_info.candidate_info)
            if email:
                cursor.execute("SELECT candidate_id FROM candidates WHERE email = ?", (email.lower(),))
                row = cursor.fetchone()
                if row:
                    candidate_id = row["candidate_id"]

            if not candidate_id:
                candidate_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO candidates (candidate_id, full_name, email, phone) VALUES (?, ?, ?, ?)",
                    (candidate_id, full_name, email.lower() if email else None, phone),
                )

        # 2. Insert Resume Info
        resume_id = str(uuid.uuid4())
        resume_parsed_json = resume_info.model_dump_json()
        cursor.execute(
            """
            INSERT INTO resume_info (resume_id, candidate_id, resume_pdf_path, resume_text, resume_parsed)
            VALUES (?, ?, ?, ?, ?)
            """,
            (resume_id, candidate_id, resume_pdf_path or "", resume_text or "", resume_parsed_json),
        )

        # 3. Insert or Update Interview record
        prep_json = interview_prep.model_dump_json()
        cursor.execute("SELECT interview_id FROM interview WHERE thread_id = ?", (thread_id,))
        existing = cursor.fetchone()

        if existing:
            interview_id = existing["interview_id"]
            cursor.execute(
                """
                UPDATE interview
                SET candidate_id = ?, resume_id = ?, target_role = ?,
                    interview_prep_topic = ?, status = 'in_progress', started_at = CURRENT_TIMESTAMP
                WHERE thread_id = ?
                """,
                (candidate_id, resume_id, target_role, prep_json, thread_id),
            )
        else:
            interview_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO interview (interview_id, candidate_id, resume_id, thread_id, target_role, interview_prep_topic, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, 'in_progress', CURRENT_TIMESTAMP)
                """,
                (interview_id, candidate_id, resume_id, thread_id, target_role, prep_json),
            )

        conn.commit()
        print(f"[SQLite] Saved initial interview session: thread_id={thread_id}, candidate_id={candidate_id}")
        return {
            "candidate_id": candidate_id,
            "resume_id": resume_id,
            "interview_id": interview_id,
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_interview_turn(thread_id: str, interview_state: InterviewState) -> bool:
    """Updates question_count, total_score, and interview_script in SQLite."""
    if not thread_id:
        return False
    init_sqlite_db()
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()
        script_json = interview_state.model_dump_json()
        cursor.execute(
            """
            UPDATE interview
            SET total_score = ?, question_count = ?, interview_script = ?
            WHERE thread_id = ?
            """,
            (interview_state.total_score, interview_state.question_count, script_json, thread_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def save_completed_interview(
    thread_id: str,
    interview_state: InterviewState,
    feedback: InterviewFeedback,
) -> bool:
    """Finalizes completed interview in SQLite."""
    if not thread_id:
        return False
    init_sqlite_db()
    conn = get_sqlite_conn()
    try:
        cursor = conn.cursor()
        script_json = interview_state.model_dump_json()
        feedback_json = feedback.model_dump_json()

        cursor.execute(
            """
            UPDATE interview
            SET status = 'completed',
                total_score = ?,
                question_count = ?,
                interview_script = ?,
                interview_feed_back = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE thread_id = ?
            """,
            (interview_state.total_score, interview_state.question_count, script_json, feedback_json, thread_id),
        )
        conn.commit()
        print(f"[SQLite] Completed interview session saved: thread_id={thread_id}")
        return True
    finally:
        conn.close()
