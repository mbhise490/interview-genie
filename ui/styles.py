CUSTOM_CSS = """
<style>
/* -------------------------------------------------------------
   INTERVIEW GENIE - MODERN UI STYLING
------------------------------------------------------------- */

/* Main Header Glow */
.genie-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.genie-subtitle {
    font-size: 1.05rem;
    color: #64748b;
    margin-bottom: 1.5rem;
}

/* Polished Cards */
.genie-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 14px 0 rgba(0, 0, 0, 0.06);
    backdrop-filter: blur(8px);
}

/* Metric Cards */
.metric-container {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
}

.metric-pill {
    flex: 1;
    background: rgba(99, 102, 241, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    text-align: center;
}

.metric-pill-label {
    font-size: 0.8rem;
    text-transform: uppercase;
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.metric-pill-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #6366f1;
}

/* Historical Progress Highlight Banner */
.history-progress-banner {
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%);
    border: 2px solid #a855f7;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin: 1.2rem 0;
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.15);
}

.history-banner-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    font-size: 1.15rem;
    color: #a855f7;
    margin-bottom: 0.5rem;
}

.history-banner-body {
    font-size: 0.96rem;
    line-height: 1.6;
}

/* Recommendation Badges */
.badge-rec {
    display: inline-block;
    padding: 0.35rem 0.85rem;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.rec-strongly-recommended {
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #86efac;
}

.rec-recommended {
    background: #dbeafe;
    color: #1d4ed8;
    border: 1px solid #93c5fd;
}

.rec-moderate-fit {
    background: #fef3c7;
    color: #b45309;
    border: 1px solid #fde68a;
}

.rec-needs-improvement {
    background: #ffedd5;
    color: #c2410c;
    border: 1px solid #fed7aa;
}

.rec-not-recommended {
    background: #fee2e2;
    color: #b91c1c;
    border: 1px solid #fca5a5;
}

/* Strength & Improvement Item Tags */
.strength-card {
    background: rgba(34, 197, 94, 0.06);
    border-left: 4px solid #22c55e;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.65rem;
    border-radius: 0 8px 8px 0;
}

.improvement-card {
    background: rgba(249, 115, 22, 0.06);
    border-left: 4px solid #f97316;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.65rem;
    border-radius: 0 8px 8px 0;
}

/* User Badge in Sidebar */
.user-badge-container {
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 1rem;
}

.user-badge-name {
    font-weight: 700;
    font-size: 1.05rem;
    color: #6366f1;
}

.user-badge-email {
    font-size: 0.85rem;
    color: #64748b;
}

/* Status Pill */
.status-pill {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
}

.status-in-progress {
    background: #e0e7ff;
    color: #4338ca;
}

.status-completed {
    background: #dcfce7;
    color: #15803d;
}
</style>
"""


def get_recommendation_badge_html(recommendation: str) -> str:
    """Returns styled HTML badge for candidate recommendation."""
    rec = (recommendation or "moderate_fit").lower()
    rec_class_map = {
        "strongly_recommended": "rec-strongly-recommended",
        "recommended": "rec-recommended",
        "moderate_fit": "rec-moderate-fit",
        "needs_improvement": "rec-needs-improvement",
        "not_recommended": "rec-not-recommended",
    }
    css_class = rec_class_map.get(rec, "rec-moderate-fit")
    label = rec.replace("_", " ").title()
    return f'<span class="badge-rec {css_class}">{label}</span>'
