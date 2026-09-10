"""Hardcoded Phase 1 data.

This lets the frontend integrate against real HTTP before the database and
skill-matching logic exist. Phase 2 replaces these with `services/` +
`repositories/` backed by PostgreSQL — the response shapes stay identical.

Values mirror the frontend demo fixtures (frontend/src/data/*.js) so switching
from mock mode to the live backend produces the same screens.
"""

# --- GET /api/market-insights -------------------------------------------------

MARKET_INSIGHTS = {
    "updatedAt": "2026-09-01",
    "topSkills": [
        {"name": "Python", "percentage": 44},
        {"name": "SQL", "percentage": 41},
        {"name": "AWS", "percentage": 29},
        {"name": "React", "percentage": 26},
        {"name": "Docker", "percentage": 22},
    ],
    "topRoles": [
        {"name": "Data Engineer", "percentage": 38},
        {"name": "Data Analyst", "percentage": 31},
        {"name": "Software Engineer", "percentage": 27},
        {"name": "Product Manager", "percentage": 18},
        {"name": "ML Engineer", "percentage": 15},
    ],
    "topLocations": [
        {"name": "Frankfurt", "percentage": 34},
        {"name": "Berlin", "percentage": 30},
        {"name": "Munich", "percentage": 21},
        {"name": "Remote (EU)", "percentage": 19},
        {"name": "Hamburg", "percentage": 12},
    ],
    "trends": [
        {"label": "AI / ML tooling demand", "percentage": 62, "direction": "up"},
        {"label": "Cloud infrastructure roles", "percentage": 47, "direction": "up"},
        {"label": "Average salary (YoY)", "percentage": 8, "direction": "up"},
        {"label": "Entry-level openings", "percentage": 6, "direction": "down"},
    ],
}


# --- POST /api/analyze  &  GET /api/roles ------------------------------------

# role label -> canonical required skills. Phase 2 derives/enriches this from the
# job-market dataset; keep the curated map as the reliable baseline.
ROLE_REQUIRED_SKILLS: dict[str, list[str]] = {
    "Data Analyst": ["SQL", "Excel", "Python", "Tableau", "Statistics"],
    "Data Engineer": ["Python", "SQL", "Spark", "Airflow", "AWS", "Docker"],
    "Business Analyst": ["SQL", "Excel", "Power BI", "Stakeholder Management", "Statistics"],
    "Software Engineer": ["JavaScript", "React", "Node.js", "SQL", "Git", "REST API"],
    "Product Manager": ["Roadmapping", "SQL", "Stakeholder Management", "Agile", "Analytics"],
}


def _slug(label: str) -> str:
    return label.lower().replace(" ", "-")


ROLES = [
    {"id": _slug(label), "label": label, "requiredSkills": skills}
    for label, skills in ROLE_REQUIRED_SKILLS.items()
]
