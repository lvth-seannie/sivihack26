"""Career analysis: skill gap + roadmap + recommendation.

Phase 2: deterministic. Required skills come from the curated role map
(api/data/role_skill_map.py); the gap and roadmap are pure Python
(api/services/); the recommendation is templated
(api/services/recommendation.py).

Phase 3: replace the templated recommendation and the roadmap descriptions
with api/ai/openai_client.py, keeping this deterministic path as the fallback.
"""
from ninja import Router
from ninja.errors import HttpError

from api.data.role_skill_map import known_roles
from api.schemas import AnalyzeIn, AnalyzeOut
from api.services import roadmap
from api.services.recommendation import fallback as fallback_recommendation
from api.services.skill_matching import analyse

router = Router()

# `currentSkills` is user input that will reach an LLM prompt in Phase 3 —
# bound it now. See BACKEND_SPEC §4.2.5.
_MAX_SKILLS = 50
_MAX_SKILL_LEN = 60


def _clean_skills(raw: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in raw[:_MAX_SKILLS]:
        text = "".join(ch for ch in item if ch.isprintable()).strip()[:_MAX_SKILL_LEN]
        if text:
            cleaned.append(text)
    return cleaned


@router.post("/analyze", response=AnalyzeOut)
def analyze(request, payload: AnalyzeIn):
    target_role = payload.targetRole.strip()
    skills = _clean_skills(payload.currentSkills)

    if not target_role or not skills:
        raise HttpError(422, "targetRole and at least one skill are required.")

    if target_role not in known_roles():
        known = ", ".join(known_roles())
        raise HttpError(400, f"Unknown targetRole '{target_role}'. Known roles: {known}")

    gap = analyse(target_role, skills)
    return {
        "matchScore": gap.match_score,
        "strengths": gap.strengths,
        "missingSkills": gap.missing,
        "roadmap": roadmap.build(gap.missing),
        "recommendation": fallback_recommendation(target_role, gap),
    }
