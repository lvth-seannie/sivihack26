"""Deterministic recommendation text.

This is the Phase 3 fallback: when OpenAI is unavailable (no key, timeout,
rate limit) the /analyze route returns this instead of failing.
"""
from __future__ import annotations

from api.services.skill_matching import SkillGap


def fallback(target_role: str, gap: SkillGap) -> str:
    if not gap.missing:
        return (
            f"You already meet every core skill requirement for {target_role}. "
            f"Target senior-level or specialised openings to stand out further."
        )
    focus = " and ".join(gap.missing[:2])
    return (
        f"You already cover {len(gap.strengths)} of {len(gap.required)} core skills "
        f"for {target_role}. Focus next on {focus} to close the biggest gap and "
        f"become competitive for this role within 3-6 months."
    )
