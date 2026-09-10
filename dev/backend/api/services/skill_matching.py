"""Skill-gap computation: required ∩ user, required − user, score.

Pure functions — no HTTP, no DB. `diff()` is the testable core; `analyse()` is
the entry point the /analyze route calls. Skills are compared on their
normalised form but returned in their canonical display form (from the role
map), per BACKEND_SPEC §4.3.
"""
from __future__ import annotations

from dataclasses import dataclass

from api.data.role_skill_map import required_skills_for_role
from api.services.skills import normalize


@dataclass
class SkillGap:
    required: list[str]
    strengths: list[str]
    missing: list[str]
    match_score: int


def diff(required: list[str], current: list[str]) -> SkillGap:
    owned = {normalize(s) for s in current if s and s.strip()}
    strengths: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()
    for skill in required:
        key = normalize(skill)
        if key in seen:
            continue
        seen.add(key)
        (strengths if key in owned else missing).append(skill)

    total = len(strengths) + len(missing)
    score = round(len(strengths) / total * 100) if total else 0
    return SkillGap(required=list(required), strengths=strengths, missing=missing, match_score=score)


def analyse(target_role: str, current_skills: list[str]) -> SkillGap:
    required = required_skills_for_role(target_role) or []
    return diff(required, current_skills)
