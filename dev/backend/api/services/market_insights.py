"""Assemble the GET /api/market-insights payload from the job dataset.

Aggregates `jobs` / `job_skill` into the top skills / roles / locations the
frontend renders. Falls back to api.stub_data.MARKET_INSIGHTS when the dataset
is empty or unreachable, so the endpoint always returns a usable shape. The
computed payload is cached in-process for CACHE_TTL seconds.
"""
from __future__ import annotations

import time

from api.data.role_skill_map import classify_title
from api.repositories import jobs_repo
from api.services.skills import display, normalize
from api.stub_data import MARKET_INSIGHTS

CACHE_TTL = 60 * 60  # seconds
_TOP_N = 5

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
        "trends": [],  # no time dimension in the dataset — see BACKEND_SPEC §3.1
    }
