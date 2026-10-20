# Interview Genie — Frontend

A React + Vite frontend for the **Interview Genie** mock-interview platform. White-and-green design system, fully responsive, connected to the FastAPI backend via HTTP Basic auth.

## Tech Stack

- **React 18** with Vite
- **React Router v6** for routing
- **Axios** for API calls (HTTP Basic auth)
- **Tailwind CSS** for styling
- **Lucide React** for icons

## Getting Started

### Prerequisites

- **Node.js** 18+ and npm

### Setup

```bash
cd frontend
cp .env.example .env        # edit VITE_API_BASE_URL if needed
npm install
npm run dev                  # starts at http://localhost:5173
```

### Environment Variables

| Variable            | Default                  | Description                |
|---------------------|--------------------------|----------------------------|
| `VITE_API_BASE_URL` | `http://localhost:8000`  | Backend API base URL       |

### Build for Production

```bash
npm run build    # outputs to dist/
npm run preview  # preview the production build
```

## Folder Structure

```
frontend/
├── public/
├── src/
│   ├── api/              # Axios instance + per-resource API modules
│   │   ├── client.js     #   Configured axios with Basic auth interceptors
│   │   ├── auth.js       #   login, register
│   │   └── interviews.js #   CRUD + interview flow endpoints
│   ├── components/       # Reusable UI components
│   │   ├── Button.jsx    #   Variant-based button (primary/secondary/danger)
│   │   ├── Card.jsx      #   Bordered white card
│   │   ├── EmptyState.jsx
│   │   ├── Footer.jsx
│   │   ├── Input.jsx     #   Form input with error, password toggle
│   │   ├── Layout.jsx    #   Navbar + Outlet + Footer shell
│   │   ├── Loader.jsx    #   Spinner + message
│   │   ├── Navbar.jsx    #   Sticky top nav
│   │   └── Toast.jsx     #   Success/error notification
│   ├── context/          # React Context providers
│   │   ├── AuthContext.jsx
│   │   └── ToastContext.jsx
│   ├── hooks/
│   │   └── useAuth.js
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── DashboardPage.jsx     # List all interviews
│   │   ├── NewInterviewPage.jsx  # Upload resume + target role
│   │   ├── InterviewPage.jsx     # Live chat-style interview
│   │   ├── FeedbackPage.jsx      # Detailed feedback + transcript
│   │   └── NotFoundPage.jsx
│   ├── routes/
│   │   └── ProtectedRoute.jsx
│   ├── styles/
│   │   └── index.css             # Tailwind directives + theme layer
│   ├── utils/
│   │   └── helpers.js            # Error extraction, date format, validation
│   ├── App.jsx
│   └── main.jsx
├── .env.example
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
└── vite.config.js
```

## Pages & Endpoints Connected

| Page               | Endpoints Used                                                        |
|--------------------|-----------------------------------------------------------------------|
| Login              | `POST /auth/login` (HTTP Basic)                                      |
| Register           | `POST /auth/register`                                                |
| Dashboard          | `GET /interviews`                                                    |
| New Interview      | `POST /interviews` (multipart: target_role + resume PDF)             |
| Interview (chat)   | `POST /interviews/{id}/start`, `POST /interviews/{id}/answer`, `POST /interviews/{id}/end` |
| Feedback           | `GET /interviews/{id}/feedback`                                      |

## Enable CORS on the Backend

Add this to `src/interview_genie_v2/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from interview_genie_v2.api.routes import router, interview_router

app = FastAPI(title="Interview Genie")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(interview_router)
```

## Design System

- **Background**: Pure white `#FFFFFF` on all pages
- **Primary buttons**: Green `#16A34A`, hover `#15803D`, active `#166534`
- **Secondary buttons**: White bg, green border + text
- **Text**: `#111827` headings, `#4B5563` body
- **Cards/inputs**: White, `#E5E7EB` border, rounded, subtle shadow
- **Focus rings**: Green
- **Font**: Inter (Google Fonts)

All colors are defined in `tailwind.config.js` — no hardcoded values in components.

## Backend Gaps

- **No profile/settings endpoint** — the backend has no route to update username, email, or password
- **No JWT/token auth** — the backend uses HTTP Basic (email + password on every request); credentials are stored in localStorage

## Assumptions

1. The backend runs on `http://localhost:8000` by default
2. HTTP Basic credentials (email + password) are stored in `localStorage` since there's no token endpoint
3. The `FeedbackOut.details` field contains the written summary, communication feedback, and improvement areas. Strengths and weaknesses are returned separately.
4. Interview transcript messages have `{ role, content }` structure
