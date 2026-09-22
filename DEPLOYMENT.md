# 🚀 Deployment Guide — Interview Genie on Streamlit Community Cloud

This guide provides step-by-step instructions to deploy **Interview Genie** to **Streamlit Community Cloud** ([share.streamlit.io](https://share.streamlit.io)) so anyone can access your AI Mock Interview platform from any web browser.

---

## 🏗️ Cloud Architecture Highlights

- **Root Entrypoint**: `streamlit_app.py` is configured at the repository root. Streamlit Cloud auto-detects it.
- **Standalone Cloud Execution**: The application uses a hybrid execution client. On Streamlit Cloud, it executes the LangGraph workflow, interviewer agent, and feedback evaluator **in-process**, requiring **zero external FastAPI servers**.
- **Universal Database Engine**: When deployed to Streamlit Cloud (Debian Linux container), the app automatically uses the self-contained **SQLite** cloud database. No external SQL Server configuration is required!
- **Secrets Management**: Configuration is loaded directly from Streamlit Cloud's built-in Secrets management (`st.secrets`).

---

## 📋 Step-by-Step Deployment Instructions

### Step 1: Push Code to a GitHub Repository

If you haven't already pushed this project to GitHub:

1. Create a **New Repository** on [GitHub](https://github.com/new) (e.g. named `interview-genie`).
2. Open your terminal in this project folder (`d:\Mine\projects\Interview Genie`):
   ```bash
   git init
   git add .
   git commit -m "feat: complete Interview Genie with authentication, feedback progression, and Streamlit UI"
   git branch -M main
   git remote add origin https://github.com/<your-username>/interview-genie.git
   git push -u origin main
   ```
   *(Note: The `.gitignore` file already prevents your `.env` and sensitive credentials from being committed).*

---

### Step 2: Log In to Streamlit Community Cloud

1. Visit **[share.streamlit.io](https://share.streamlit.io)**.
2. Sign in with your **GitHub account**.
3. Authorize Streamlit to access your repositories if prompted.

---

### Step 3: Create a New App

1. Click the **"New app"** button (or **"Create app"**).
2. Configure the deployment settings:
   - **Repository**: `<your-username>/interview-genie`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL** (optional): Customize your subdomain (e.g. `interview-genie-ai.streamlit.app`).

---

### Step 4: Configure Secrets (Required)

Before launching, add your OpenAI API key to Streamlit Cloud:

1. In the deployment screen, click **"Advanced settings..."** (or go to **Settings ➔ Secrets** after creating).
2. Paste the following into the **Secrets** text box:

```toml
# Required: Your OpenAI API Key
OPENAI_API_KEY = "sk-proj-YOUR_ACTUAL_OPENAI_API_KEY_HERE"

# Required: Secret key for signing candidate JWT tokens
JWT_SECRET_KEY = "interview_genie_super_secret_jwt_key_2026_change_me"

# Optional: Set to true if you want to explicitly enforce SQLite in cloud
USE_SQLITE = "true"
```

3. Click **"Save"**.

---

### Step 5: Deploy & Launch!

1. Click **"Deploy!"**.
2. Streamlit Cloud will:
   - Spin up a clean container.
   - Install dependencies from `requirements.txt`.
   - Run `streamlit_app.py`.
3. Within 1–2 minutes, your live web application will be live at:
   `https://<your-custom-name>.streamlit.app`

---

## 🔍 Verifying Your Cloud Deployment

Once deployed, you can verify:
1. **Candidate Sign Up**: Create a new account with email & password.
2. **Practice Interview**: Select a target role (e.g. *Senior Backend Engineer*), upload a PDF resume (or use the included sample resume), and answer questions.
3. **Historical Progress Comparison**: Complete an interview for a role, then start a second interview for the **exact same role**. The Evaluator will automatically analyze your growth trajectory compared to the first attempt!
4. **History & Growth Tab**: View all your completed interviews preserved in the database.
