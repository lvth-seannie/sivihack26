"""Skill-string normalisation — the core of match quality.

`normalize()` maps a raw skill string to a canonical comparison key; `display()`
maps a key back to a human label. Both the curated role map and the user's typed
skills pass through the same funnel, so "js", "JavaScript" and "  javascript "
all compare equal.

Keep the alias map conservative and unit-tested — it drives every match score
and every Market Insights number.
"""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")

# raw form (already lowercased + whitespace-collapsed) -> canonical key
_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ecmascript": "javascript",
    "ts": "typescript",
    "py": "python",
    "node": "node.js",
    "nodejs": "node.js",
    "node js": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "golang": "go",
    "csharp": "c#",
    "c sharp": "c#",
    "cpp": "c++",
    # SQL family collapses to "sql" for matching purposes (see BACKEND_SPEC §4.3)
    "postgres": "sql",
    "postgresql": "sql",
    "psql": "sql",
    "mysql": "sql",
    "mariadb": "sql",
    "t-sql": "sql",
    "tsql": "sql",
    "pl/sql": "sql",
    "plsql": "sql",
    "ms sql": "sql",
    "sql server": "sql",
    "k8s": "kubernetes",
    "gcp": "google cloud",
    "google cloud platform": "google cloud",
    "amazon web services": "aws",
    "aws cloud": "aws",
    "powerbi": "power bi",
    "power-bi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "rest": "rest api",
    "restful": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest apis": "rest api",
    "rest-api": "rest api",
    "cicd": "ci/cd",
    "ci cd": "ci/cd",
    "ci-cd": "ci/cd",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "oop": "object-oriented programming",
}

# canonical key -> display label (falls back to smart title-case when absent)
_DISPLAY: dict[str, str] = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "node.js": "Node.js",
    "python": "Python",
    "java": "Java",
    "sql": "SQL",
    "nosql": "NoSQL",
    "aws": "AWS",
    "react": "React",
    "c#": "C#",
    "c++": "C++",
    "css": "CSS",
    "html": "HTML",
    "go": "Go",
    "php": "PHP",
    "google cloud": "Google Cloud",
    "power bi": "Power BI",
    "rest api": "REST API",
    "ci/cd": "CI/CD",
    "etl": "ETL",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "natural language processing": "NLP",
    "object-oriented programming": "OOP",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "git": "Git",
    "spark": "Spark",
    "airflow": "Airflow",
    "excel": "Excel",
    "tableau": "Tableau",
    "statistics": "Statistics",
    "agile": "Agile",
    "analytics": "Analytics",
    "roadmapping": "Roadmapping",
    "stakeholder management": "Stakeholder Management",
}

_ACRONYM_MAX = 3


def normalize(skill: str) -> str:
    """Raw skill string -> canonical comparison key."""
    s = _WS.sub(" ", (skill or "").strip().lower()).strip(" .")
    return _ALIASES.get(s, s)


def display(key: str) -> str:
    """Canonical key -> human-readable label."""
    if key in _DISPLAY:
        return _DISPLAY[key]
    parts = key.split()
    return " ".join(
        p.upper() if len(p) <= _ACRONYM_MAX else p[:1].upper() + p[1:] for p in parts
    )
