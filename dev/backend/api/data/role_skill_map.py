"""Curated role -> required-skills map + free-text job-title classification.

The curated map is the reliable baseline for the demo. `required_skills_for_role`
can additionally enrich a role with high-frequency skills pulled from the job
dataset, but that is gated behind ENRICH_FROM_DATA (off by default) so the
frontend contract stays predictable.

`classify_title` buckets the dataset's messy free-text `job_title` values into
the five UI roles; it powers the `topRoles` section of Market Insights.
"""
from __future__ import annotations

import re

# role label -> canonical required skills (display form). Mirrors the frontend
# fixture in frontend/src/data/mockAnalysis.js.
ROLE_REQUIRED_SKILLS: dict[str, list[str]] = {
    "Data Analyst": ["SQL", "Excel", "Python", "Tableau", "Statistics"],
    "Data Engineer": ["Python", "SQL", "Spark", "Airflow", "AWS", "Docker"],
    "Business Analyst": ["SQL", "Excel", "Power BI", "Stakeholder Management", "Statistics"],
    "Software Engineer": ["JavaScript", "React", "Node.js", "SQL", "Git", "REST API"],
    "Product Manager": ["Roadmapping", "SQL", "Stakeholder Management", "Agile", "Analytics"],
}

# First pattern to match a title wins — order matters (more specific first).
_TITLE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Data Engineer", re.compile(
        r"data\s*engineer|analytics\s*engineer|\betl\b|data\s*platform|big\s*data", re.I)),
    ("Data Analyst", re.compile(
        r"data\s*analyst|data\s*analytics|business\s*intelligence|\bbi\b|reporting\s*analyst", re.I)),
    ("Business Analyst", re.compile(
        r"business\s*analyst|business\s*systems\s*analyst|process\s*analyst|requirements\s*analyst", re.I)),
    ("Product Manager", re.compile(
        r"product\s*manager|product\s*owner|product\s*lead|\bpo\b|\bpm\b", re.I)),
    ("Software Engineer", re.compile(
        r"software\s*engineer|software\s*developer|back[\s-]*end|front[\s-]*end|full[\s-]*stack|"
        r"web\s*developer|application\s*developer|\bsde\b|programmer", re.I)),
]

# --- optional data-driven enrichment ---------------------------------------
ENRICH_FROM_DATA = False
_ENRICH_MIN_SHARE = 0.30   # skill must appear in >= 30% of the role's postings
_MAX_REQUIRED = 8


def known_roles() -> list[str]:
    return list(ROLE_REQUIRED_SKILLS)


def classify_title(job_title: str | None) -> str | None:
    for role, pattern in _TITLE_PATTERNS:
        if pattern.search(job_title or ""):
            return role
    return None


def required_skills_for_role(role: str) -> list[str] | None:
    base = ROLE_REQUIRED_SKILLS.get(role)
    if base is None or not ENRICH_FROM_DATA:
        return base
    return _enrich(role, base)


def role_catalogue() -> list[dict]:
    return [
        {"id": _slug(label), "label": label, "requiredSkills": required_skills_for_role(label)}
        for label in ROLE_REQUIRED_SKILLS
    ]


def _slug(label: str) -> str:
    return label.lower().replace(" ", "-")


def _enrich(role: str, base: list[str]) -> list[str]:
    from api.repositories import jobs_repo
    from api.services.skills import display, normalize

    titles = [t for t, _ in jobs_repo.title_counts() if classify_title(t) == role]
    role_jobs = sum(n for t, n in jobs_repo.title_counts() if classify_title(t) == role)
    counts = jobs_repo.skill_counts_for_titles(titles)
    if not role_jobs or not counts:
        return base

    have = {normalize(s) for s in base}
    extra = sorted(
        (
            (display(normalize(sk)), n)
            for sk, n in counts
            if normalize(sk) not in have and n / role_jobs >= _ENRICH_MIN_SHARE
        ),
        key=lambda pair: -pair[1],
    )
    merged = list(base)
    for label, _ in extra:
        if len(merged) >= _MAX_REQUIRED:
            break
        merged.append(label)
    return merged
