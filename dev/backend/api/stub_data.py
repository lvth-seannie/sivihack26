"""Fallback fixture for GET /api/market-insights.

Served verbatim when the job dataset is empty or unreachable (see
api/services/market_insights.py). Values mirror the frontend demo fixture
(frontend/src/data/mockInsights.js) so a cold backend produces the same screen
as the frontend's offline mock mode.

The role map that used to live here moved to api/data/role_skill_map.py.
"""

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
