import os
import json
import streamlit as st

from ui.api_client import GenieAPIClient
from ui.styles import CUSTOM_CSS, get_recommendation_badge_html
from ui.utils import save_uploaded_resume, generate_thread_id, get_default_sample_resume_path

# =============================================================================
# Page Configuration & Styling
# =============================================================================
st.set_page_config(
    page_title="Interview Genie — AI Mock Interviewer",
    page_icon="🧞",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize API Client
api_client = GenieAPIClient()

# =============================================================================
# Session State Initialization
# =============================================================================
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = None
if "target_role" not in st.session_state:
    st.session_state["target_role"] = ""
if "resume_path" not in st.session_state:
    st.session_state["resume_path"] = None
if "interview_status" not in st.session_state:
    st.session_state["interview_status"] = "not_started"  # not_started, in_progress, completed
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []  # list of dicts: {"role": "interviewer"|"candidate", "text": str, "score": float}
if "current_question" not in st.session_state:
    st.session_state["current_question"] = None
if "question_count" not in st.session_state:
    st.session_state["question_count"] = 0
if "total_score" not in st.session_state:
    st.session_state["total_score"] = 0.0
if "feedback" not in st.session_state:
    st.session_state["feedback"] = None


# =============================================================================
# Sidebar: Brand, Health & Authentication
# =============================================================================
with st.sidebar:
    st.markdown('<div class="genie-title">🧞 Interview Genie</div>', unsafe_allow_html=True)
    st.markdown('<div class="genie-subtitle">Adaptive Mock Interview Platform</div>', unsafe_allow_html=True)

    # 1. Database & Backend Health
    health = api_client.validate_db()
    if health.get("status") == "connected":
        st.success(f"🟢 Database: {health.get('database')} Connected", icon="✅")
        with st.expander("Database Status"):
            st.caption(f"Server: {health.get('server_version', 'SQL Server')[:45]}...")
            tbls = health.get("tables", {})
            st.write(f"- **Candidates**: {tbls.get('candidates', 0)}")
            st.write(f"- **Resumes**: {tbls.get('resume_info', 0)}")
            st.write(f"- **Interviews**: {tbls.get('interview', 0)}")
    else:
        st.error(f"🔴 DB Offline: {health.get('error', 'Unable to reach backend')}", icon="⚠️")

    st.markdown("---")

    # 2. Candidate Authentication
    if st.session_state["token"] and st.session_state["user"]:
        user = st.session_state["user"]
        st.markdown(
            f"""
            <div class="user-badge-container">
                <div class="user-badge-name">👤 {user.get('full_name', 'Candidate')}</div>
                <div class="user-badge-email">{user.get('email', '')}</div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">ID: {user.get('candidate_id', '')[:8]}...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["user"] = None
            st.rerun()
    else:
        st.markdown("### 🔐 Candidate Sign In")
        auth_tab1, auth_tab2 = st.tabs(["Sign In", "Sign Up"])

        with auth_tab1:
            with st.form("login_form"):
                login_email = st.text_input("Email", placeholder="you@example.com")
                login_password = st.text_input("Password", type="password")
                login_btn = st.form_submit_button("Sign In", use_container_width=True)

                if login_btn:
                    if not login_email or not login_password:
                        st.warning("Please provide email and password.")
                    else:
                        try:
                            auth_res = api_client.login(login_email, login_password)
                            st.session_state["token"] = auth_res["access_token"]
                            profile = api_client.get_profile(auth_res["access_token"])
                            st.session_state["user"] = profile
                            st.success("Signed in successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        with auth_tab2:
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="Jane Doe")
                reg_email = st.text_input("Email", placeholder="you@example.com")
                reg_phone = st.text_input("Phone (optional)", placeholder="+1-555-0199")
                reg_password = st.text_input("Password", type="password")
                reg_btn = st.form_submit_button("Create Account", use_container_width=True)

                if reg_btn:
                    if not reg_email or not reg_password:
                        st.warning("Email and password are required.")
                    else:
                        try:
                            auth_res = api_client.register(
                                email=reg_email,
                                password=reg_password,
                                full_name=reg_name,
                                phone=reg_phone,
                            )
                            st.session_state["token"] = auth_res["access_token"]
                            profile = api_client.get_profile(auth_res["access_token"])
                            st.session_state["user"] = profile
                            st.success("Account created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    st.markdown("---")

    # Navigation Mode
    nav_mode = st.radio(
        "Navigation",
        options=["🎙️ Practice Interview", "📊 My History & Growth", "⚙️ System & DB Health"],
        index=0,
    )


# =============================================================================
# Helper: Reset Interview State
# =============================================================================
def reset_interview():
    st.session_state["thread_id"] = None
    st.session_state["interview_status"] = "not_started"
    st.session_state["conversation"] = []
    st.session_state["current_question"] = None
    st.session_state["question_count"] = 0
    st.session_state["total_score"] = 0.0
    st.session_state["feedback"] = None


# =============================================================================
# VIEW 1: Practice Interview
# =============================================================================
if nav_mode == "🎙️ Practice Interview":
    st.markdown('<div class="genie-title">Mock Interview Studio</div>', unsafe_allow_html=True)
    st.caption("AI-powered adaptive interview customized to your resume and role.")

    # ---------------------------------------------------------
    # STAGE A: Pre-Interview Setup
    # ---------------------------------------------------------
    if st.session_state["interview_status"] == "not_started":
        st.markdown("### 1. Configure Your Session")

        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown("#### 📄 Resume Source")
            resume_choice = st.radio(
                "Select resume input method:",
                options=["Upload PDF Resume", "Use Default Sample Resume"],
                index=0,
            )

            resolved_resume_path = None
            if resume_choice == "Upload PDF Resume":
                uploaded_pdf = st.file_uploader("Upload your resume in PDF format", type=["pdf"])
                if uploaded_pdf is not None:
                    cid = st.session_state["user"].get("candidate_id") if st.session_state["user"] else None
                    saved_path = save_uploaded_resume(uploaded_pdf, candidate_id=cid)
                    resolved_resume_path = saved_path
                    st.success(f"Resume saved: {os.path.basename(saved_path)}")
            else:
                sample_path = get_default_sample_resume_path()
                if sample_path and os.path.exists(sample_path):
                    resolved_resume_path = sample_path
                    st.info(f"Using pre-configured sample resume: `{os.path.basename(sample_path)}`")
                else:
                    st.warning("No sample_resume.pdf found in project root. Please upload a PDF.")

        with col2:
            st.markdown("#### 🎯 Target Role")
            role_options = [
                "Senior Backend Engineer (Python/FastAPI)",
                "Full Stack Developer (React & Node.js)",
                "Data Scientist (Machine Learning)",
                "DevOps / Cloud Platform Engineer",
                "Frontend Engineer (React/TypeScript)",
                "Other (Custom Role)",
            ]
            selected_role = st.selectbox("Select Target Job Role:", role_options, index=0)

            final_role = selected_role
            if selected_role == "Other (Custom Role)":
                custom_role = st.text_input("Enter Custom Target Role:", placeholder="e.g. Distributed Systems Architect")
                final_role = custom_role.strip()

            st.caption(
                "💡 **Adaptive Progression**: If you have interviewed for this exact role before, "
                "the Evaluator will compare your performance against previous feedback!"
            )

        st.markdown("---")

        start_col1, start_col2, _ = st.columns([1, 1, 2])
        with start_col1:
            can_start = bool(resolved_resume_path and final_role)
            if st.button("🚀 Start Interview", type="primary", use_container_width=True, disabled=not can_start):
                with st.spinner("Analyzing resume and generating customized interview preparation..."):
                    new_thread_id = generate_thread_id(prefix="session")
                    token = st.session_state.get("token")
                    try:
                        res = api_client.start_interview(
                            resume_pdf_path=resolved_resume_path,
                            target_role=final_role,
                            thread_id=new_thread_id,
                            token=token,
                        )
                        st.session_state["thread_id"] = new_thread_id
                        st.session_state["target_role"] = final_role
                        st.session_state["resume_path"] = resolved_resume_path
                        st.session_state["interview_status"] = res.get("status", "in_progress")
                        first_q = res.get("question")
                        st.session_state["current_question"] = first_q
                        st.session_state["conversation"] = [
                            {"role": "interviewer", "text": first_q, "score": None}
                        ]
                        st.session_state["question_count"] = res.get("question_count", 0)
                        st.session_state["total_score"] = res.get("total_score", 0.0)
                        st.session_state["feedback"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error starting interview: {e}")

    # ---------------------------------------------------------
    # STAGE B: In-Progress Live Interview Room
    # ---------------------------------------------------------
    elif st.session_state["interview_status"] == "in_progress":
        # Header Status Bar
        hcol1, hcol2, hcol3 = st.columns([2, 1, 1])
        with hcol1:
            st.markdown(f"### 🎯 Role: **{st.session_state['target_role']}**")
            st.caption(f"Session Thread: `{st.session_state['thread_id']}`")
        with hcol2:
            q_cnt = st.session_state.get("question_count", 0)
            st.metric("Questions Answered", q_cnt)
        with hcol3:
            tot_sc = st.session_state.get("total_score", 0.0)
            avg_sc = (tot_sc / q_cnt) if q_cnt > 0 else 0.0
            st.metric("Avg Score", f"{avg_sc:.1f} / 10" if q_cnt > 0 else "—")

        st.markdown("---")

        # Chat conversation transcript
        for turn in st.session_state["conversation"]:
            if turn["role"] == "interviewer":
                with st.chat_message("assistant", avatar="🧞"):
                    st.write(turn["text"])
            elif turn["role"] == "candidate":
                with st.chat_message("user", avatar="👤"):
                    st.write(turn["text"])
                    if turn.get("score") is not None:
                        st.caption(f"⭐ **Turn Score**: {turn['score']:.1f} / 10")

        # Candidate Answer Box
        st.markdown("#### ✍️ Your Answer")
        answer_input = st.text_area(
            "Respond to the interviewer's question:",
            height=140,
            placeholder="Type your detailed answer here... Include technical context, trade-offs, and examples.",
            key="candidate_answer_input",
        )

        bcol1, bcol2, _ = st.columns([1, 1, 2])
        with bcol1:
            submit_ans = st.button("Submit Answer", type="primary", use_container_width=True, disabled=not answer_input.strip())
        with bcol2:
            conclude_early = st.button("End & Evaluate Now", use_container_width=True)

        if submit_ans and answer_input.strip():
            with st.spinner("Evaluating response and preparing next question..."):
                try:
                    res = api_client.submit_answer(
                        thread_id=st.session_state["thread_id"],
                        answer=answer_input.strip(),
                        token=st.session_state.get("token"),
                    )

                    # Update conversation transcript
                    conv = st.session_state["conversation"]
                    # Add candidate answer to previous turn
                    conv.append({"role": "candidate", "text": answer_input.strip(), "score": None})

                    # If next question is returned
                    new_q = res.get("question")
                    new_status = res.get("status", "in_progress")
                    new_count = res.get("question_count", st.session_state["question_count"] + 1)
                    new_total = res.get("total_score", st.session_state["total_score"])

                    # If there's a score for the turn, assign it
                    if conv and len(conv) >= 2:
                        # Estimate turn score from diff
                        diff_score = new_total - st.session_state["total_score"]
                        conv[-1]["score"] = max(0.0, diff_score)

                    if new_q and new_status != "completed":
                        conv.append({"role": "interviewer", "text": new_q, "score": None})
                        st.session_state["current_question"] = new_q

                    st.session_state["question_count"] = new_count
                    st.session_state["total_score"] = new_total
                    st.session_state["interview_status"] = new_status
                    if res.get("feedback"):
                        st.session_state["feedback"] = res.get("feedback")

                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting answer: {e}")

        if conclude_early:
            with st.spinner("Concluding interview and generating comprehensive evaluation..."):
                try:
                    end_res = api_client.end_interview(
                        thread_id=st.session_state["thread_id"],
                        token=st.session_state.get("token"),
                    )
                    st.session_state["interview_status"] = "completed"
                    st.session_state["feedback"] = end_res.get("feedback")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error ending interview: {e}")

    # ---------------------------------------------------------
    # STAGE C: Completed Evaluation Dashboard
    # ---------------------------------------------------------
    elif st.session_state["interview_status"] == "completed":
        st.balloons()
        st.markdown("## 🏁 Interview Concluded — Performance Evaluation")

        fb = st.session_state.get("feedback") or {}
        if not fb and st.session_state.get("thread_id"):
            try:
                fb = api_client.get_feedback(st.session_state["thread_id"])
                st.session_state["feedback"] = fb
            except Exception:
                pass

        if fb:
            rec = fb.get("recommendation", "moderate_fit")
            score = fb.get("overall_score", 0.0)
            summary = fb.get("overall_summary", "No summary provided.")
            hist_progress = fb.get("historical_progress")

            # Top Summary Cards
            fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
            with fcol1:
                st.markdown("#### Fit Recommendation")
                st.markdown(get_recommendation_badge_html(rec), unsafe_allow_html=True)
            with fcol2:
                st.metric("Overall Score", f"{score:.1f} / 10")
            with fcol3:
                st.markdown("#### Target Role")
                st.info(f"**{st.session_state.get('target_role', 'Software Engineer')}**")

            # Historical Progress Banner (if candidate previously practiced this exact role)
            if hist_progress:
                st.markdown(
                    f"""
                    <div class="history-progress-banner">
                        <div class="history-banner-header">
                            <span>📈 Role-Specific Historical Progress</span>
                        </div>
                        <div class="history-banner-body">
                            {hist_progress}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Executive Summary
            st.markdown("### 📋 Executive Summary")
            st.write(summary)

            # Strengths & Improvement Areas
            scol1, scol2 = st.columns(2, gap="large")

            with scol1:
                st.markdown("### 🌟 Key Strengths")
                strengths = fb.get("strengths", [])
                if strengths:
                    for s in strengths:
                        cat = s.get("area", "Technical")
                        sc = s.get("score", 0.0)
                        obs = s.get("observation", "")
                        st.markdown(
                            f"""
                            <div class="strength-card">
                                <b>{cat}</b> <span style="float: right; color: #16a34a; font-weight: 700;">{sc:.1f} / 10</span><br/>
                                <span style="font-size: 0.9rem; color: #475569;">{obs}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No specific strengths recorded.")

            with scol2:
                st.markdown("### 🎯 Areas for Improvement")
                improvements = fb.get("improvement_areas", [])
                if improvements:
                    for imp in improvements:
                        cat = imp.get("area", "Technical")
                        rec_note = imp.get("recommendation", "")
                        prio = imp.get("priority", "medium").upper()
                        st.markdown(
                            f"""
                            <div class="improvement-card">
                                <b>{cat}</b> <span style="float: right; color: #ea580c; font-weight: 700;">{prio} PRIORITY</span><br/>
                                <span style="font-size: 0.9rem; color: #475569;">{rec_note}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No specific areas for improvement recorded.")

        else:
            st.info("Evaluation data is still being processed or not available.")

        st.markdown("---")
        if st.button("Start Another Interview", type="primary"):
            reset_interview()
            st.rerun()


# =============================================================================
# VIEW 2: My History & Growth
# =============================================================================
elif nav_mode == "📊 My History & Growth":
    st.markdown('<div class="genie-title">Candidate History & Growth Tracking</div>', unsafe_allow_html=True)
    st.caption("Review your completed interviews, role progression, and evaluator feedback stored in SQL Server.")

    token = st.session_state.get("token")
    if not token:
        st.warning("Please sign in or register in the sidebar to view your interview history.")
    else:
        try:
            profile = api_client.get_profile(token)
            st.session_state["user"] = profile
            interviews = profile.get("interviews", [])

            # Summary Metrics
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric("Total Interviews", len(interviews))
            with mcol2:
                roles = set(iv.get("target_role") for iv in interviews if iv.get("target_role"))
                st.metric("Roles Practiced", len(roles))
            with mcol3:
                scores = [float(iv.get("total_score", 0.0)) for iv in interviews if iv.get("status") == "completed"]
                best_score = max(scores) if scores else 0.0
                st.metric("Highest Total Score", f"{best_score:.1f}")

            st.markdown("---")

            if not interviews:
                st.info("You haven't completed any interviews yet. Head over to **Practice Interview** to get started!")
            else:
                # Role filter
                all_roles = ["All Roles"] + sorted(list(roles))
                role_filter = st.selectbox("Filter by Target Role:", all_roles)

                filtered_ivs = interviews
                if role_filter != "All Roles":
                    filtered_ivs = [iv for iv in interviews if iv.get("target_role") == role_filter]

                st.markdown(f"### Showing **{len(filtered_ivs)}** session(s):")

                for iv in filtered_ivs:
                    role = iv.get("target_role", "Unknown Role")
                    status = iv.get("status", "in_progress")
                    score = float(iv.get("total_score", 0.0))
                    q_count = iv.get("question_count", 0)
                    started = iv.get("started_at", "—")
                    rec = iv.get("recommendation")
                    summary = iv.get("overall_summary")
                    thread_id = iv.get("thread_id")

                    badge_html = get_recommendation_badge_html(rec) if rec else ""

                    with st.expander(f"💼 {role} — Status: {status.upper()} | Score: {score:.1f} ({started[:19]})"):
                        ccol1, ccol2, ccol3 = st.columns([1, 1, 1])
                        with ccol1:
                            st.write(f"**Thread ID**: `{thread_id}`")
                            st.write(f"**Started**: {started[:19]}")
                        with ccol2:
                            st.write(f"**Questions**: {q_count}")
                            st.write(f"**Total Score**: {score:.1f}")
                        with ccol3:
                            if badge_html:
                                st.markdown(f"**Recommendation**: {badge_html}", unsafe_allow_html=True)

                        if summary:
                            st.markdown("**Overall Feedback**:")
                            st.write(summary)

        except Exception as e:
            st.error(f"Error fetching candidate profile: {e}")


# =============================================================================
# VIEW 3: System & DB Health
# =============================================================================
elif nav_mode == "⚙️ System & DB Health":
    st.markdown('<div class="genie-title">System Architecture & Database Health</div>', unsafe_allow_html=True)
    st.caption("Diagnostics for Microsoft SQL Server connection, LangGraph state, and FastAPI endpoints.")

    diag = api_client.validate_db()

    dcol1, dcol2 = st.columns(2, gap="large")

    with dcol1:
        st.markdown("### 🗄️ SQL Server Connection")
        if diag.get("status") == "connected":
            st.success("✅ Connected to Database Server")
            st.write(f"- **Database**: `{diag.get('database')}`")
            st.write(f"- **Server Version**: {diag.get('server_version')}")
            tbls = diag.get("tables", {})
            st.write(f"- **Candidates Registered**: `{tbls.get('candidates', 0)}`")
            st.write(f"- **Resumes Ingested**: `{tbls.get('resume_info', 0)}`")
            st.write(f"- **Interviews Conducted**: `{tbls.get('interview', 0)}`")
        else:
            st.error(f"❌ Connection Failed: {diag.get('error')}")

    with dcol2:
        st.markdown("### 🔌 API Configuration")
        st.write(f"- **FastAPI Base URL**: `{api_client.base_url}`")
        st.write("- **Auth Method**: JWT Bearer Tokens (HS256)")
        st.write("- **Evaluator LLM**: `gpt-5.6-luna`")
        st.write("- **Resume Parser LLM**: `gpt-4o-mini`")
        st.write("- **Historical Progress Mode**: Role-specific multi-interview comparative analysis")

    st.markdown("---")
    st.markdown("### 🛠️ Database Schema Structure")
    st.code(
        """
        candidates (candidate_id, full_name, email, phone, password_hash, created_at)
        resume_info (resume_id, candidate_id, resume_pdf_path, resume_text, resume_parsed, uploaded_at)
        interview (interview_id, candidate_id, resume_id, thread_id, target_role,
                   interview_prep_topic, interview_script, interview_feed_back,
                   status, total_score, question_count, started_at, completed_at)
        """,
        language="sql",
    )
