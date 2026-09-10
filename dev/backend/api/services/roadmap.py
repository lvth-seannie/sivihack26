"""Turn the missing-skill list into an ordered learning roadmap.

Phase 2: deterministic templated descriptions. Phase 3: descriptions come from
api/ai/openai_client.py, with this kept as the fallback.
"""
from __future__ import annotations

_PHASE_HINT = {
    0: "Start here — it unlocks most of the rest of the stack.",
    1: "Build on the fundamentals with a small end-to-end project.",
}
_LATER_HINT = "Deepen it with a portfolio-quality project once the basics are solid."


def build(missing_skills: list[str]) -> list[dict]:
    steps: list[dict] = []
    for i, skill in enumerate(missing_skills):
        hint = _PHASE_HINT.get(i, _LATER_HINT)
        steps.append(
            {
                "phase": f"Phase {i + 1}",
                "skill": skill,
                "description": (
                    f"Build working proficiency in {skill} through a focused "
                    f"project or course. {hint}"
                ),
            }
        )
    return steps
