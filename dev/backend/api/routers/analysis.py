"""Career analysis: skill gap + roadmap + recommendation.

Phase 1: deterministic stub. Required skills come from the curated map in
api.stub_data; the recommendation text is templated (no OpenAI call yet).

Phase 2: move the matching logic into api/services/skill_matching.py and source
required skills from the job-market dataset.
Phase 3: replace the templated `recommendation` with api/ai/openai_client.py,
keeping this deterministic version as the fallback.
"""
from ninja import Router
from ninja.errors import HttpError

from api.schemas import AnalyzeIn, AnalyzeOut
from api.stub_data import ROLE_REQUIRED_SKILLS

router = Router()


def _norm(skill: str) -> str:
    return skill.strip().lower()


@router.post("/analyze", response=AnalyzeOut)
def analyze(request, payload: AnalyzeIn):
    target_role = payload.targetRole.strip()
    skills = [s for s in payload.currentSkills if s.strip()]

    if not target_role or not skills:
        raise HttpError(422, "targetRole and at least one skill are required.")

    required = ROLE_REQUIRED_SKILLS.get(target_role)
    if required is None:
        known = ", ".join(ROLE_REQUIRED_SKILLS)
        raise HttpError(400, f"Unknown targetRole '{target_role}'. Known roles: {known}")

    owned = {_norm(s) for s in skills}
    strengths = [s for s in required if _norm(s) in owned]
    missing = [s for s in required if _norm(s) not in owned]
    match_score = round(len(strengths) / len(required) * 100)

    roadmap = [
        {
            "phase": f"Phase {i + 1}",
            "skill": skill,
            "description": (
                f"Build working proficiency in {skill} through a focused project or course."
            ),
        }
        for i, skill in enumerate(missing)
    ]

    if missing:
        recommendation = (
            f"You already cover {len(strengths)} of {len(required)} core skills for "
            f"{target_role}. Focus next on {' and '.join(missing[:2])} to close the biggest "
            f"gap and become competitive for this role within 3-6 months."
        )
    else:
        recommendation = (
            f"You already meet every core skill requirement for {target_role}. "
            f"Consider targeting senior-level or specialized openings to stand out further."
        )

    return {
        "matchScore": match_score,
        "strengths": strengths,
        "missingSkills": missing,
        "roadmap": roadmap,
        "recommendation": recommendation,
    }
