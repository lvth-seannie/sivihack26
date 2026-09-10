"""Assemble the GET /api/market-insights payload from the job dataset.

Aggregates `jobs` / `job_skill` into the top skills / roles / locations the
frontend renders, plus a `trends` block of point-in-time shares computed from
the snapshot (`job_level`, `job_type`/`job_location`, skill mentions) — NOT a
time series; the dataset has no time dimension (see BACKEND_SPEC §3.1).

Falls back to api.stub_data.MARKET_INSIGHTS when the dataset is empty or
unreachable, so the endpoint always returns a usable shape. The computed
payload is cached in-process for CACHE_TTL seconds.
"""
from __future__ import annotations

import re
import time

from api.data.role_skill_map import classify_title
from api.repositories import jobs_repo
from api.services.skills import display, normalize
from api.stub_data import MARKET_INSIGHTS

CACHE_TTL = 60 * 60  # seconds
_TOP_N = 5

# canonical skill keys (post-normalize) that count towards each snapshot stat
_AI_ML_SKILLS = {
    "machine learning", "deep learning", "natural language processing",
    "tensorflow", "pytorch", "scikit-learn", "keras", "mlops",
    "computer vision", "generative ai", "llm", "hugging face",
}
_CLOUD_SKILLS = {"aws", "google cloud", "azure", "kubernetes", "terraform"}

_FLEXIBLE_TYPE = re.compile(r"remote|hybrid", re.I)

_cache: dict = {"at": 0.0, "payload": None}


def get_insights(force: bool = False) -> dict:
    now = time.time()
    if not force and _cache["payload"] is not None and now - _cache["at"] < CACHE_TTL:
        return _cache["payload"]
    payload = _compute() or MARKET_INSIGHTS
    _cache.update(at=now, payload=payload)
    return payload


def clear_cache() -> None:
    _cache.update(at=0.0, payload=None)


def _pct(count: int, total: int) -> int:
    return min(100, round(count / total * 100)) if total else 0


def _rank(counts: dict[str, int], total: int, limit: int = _TOP_N) -> list[dict]:
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
    return [{"name": name, "percentage": _pct(n, total)} for name, n in top]


def _snapshot(total: int) -> list[dict]:
    """Point-in-time shares of all postings, driven by whatever the dataset
    actually carries (no assumed vocabulary). A stat is skipped when its source
    column is empty, so we never render a misleading 0%."""
    stats: list[dict] = []

    types = jobs_repo.type_counts()
    if types:
        flexible = sum(n for jt, n in types if _FLEXIBLE_TYPE.search(jt))
        stats.append(_stat("Remote or hybrid roles", flexible, total))

    # seniority mix — render the dataset's own top two job_level buckets
    for lvl, n in sorted(jobs_repo.level_counts(), key=lambda kv: -kv[1])[:2]:
        stats.append(_stat(f"{lvl.title()} roles", n, total))

    pairs = jobs_repo.job_skill_pairs()
    if pairs:
        ai_jobs: set = set()
        cloud_jobs: set = set()
        for job_id, raw in pairs:
            key = normalize(raw)
            if key in _AI_ML_SKILLS:
                ai_jobs.add(job_id)
            if key in _CLOUD_SKILLS:
                cloud_jobs.add(job_id)
        stats.append(_stat("Roles requiring AI / ML skills", len(ai_jobs), total))
        stats.append(_stat("Roles requiring cloud skills", len(cloud_jobs), total))

    return stats


def _stat(label: str, count: int, total: int) -> dict:
    return {
        "label": label,
        "percentage": _pct(count, total),
        "caption": f"{count:,} of {total:,} postings",
    }


def _compute() -> dict | None:
    total = jobs_repo.total_jobs()
    if not total:
        return None

    skills: dict[str, int] = {}
    for raw, n in jobs_repo.skill_counts():
        name = display(normalize(raw))
        skills[name] = skills.get(name, 0) + n

    roles: dict[str, int] = {}
    for title, n in jobs_repo.title_counts():
        role = classify_title(title)
        if role:
            roles[role] = roles.get(role, 0) + n

    locations: dict[str, int] = {}
    for loc, n in jobs_repo.location_counts():
        key = loc.split(",")[0].strip()
        if key:
            locations[key] = locations.get(key, 0) + n

    return {
        "updatedAt": None,  # dataset has no ingest timestamp column
        "topSkills": _rank(skills, total),
        "topRoles": _rank(roles, total),
        "topLocations": _rank(locations, total),
        "trends": _snapshot(total),
    }
