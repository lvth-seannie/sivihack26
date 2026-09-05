import { mockMarketInsights } from '../data/mockInsights'
import { generateDemoAnalysis } from '../data/mockAnalysis'

// Backend integration points (see .env.example):
// - VITE_N8N_WEBHOOK_URL     -> n8n webhook: validate input, query PostgreSQL,
//                               calculate skill gap, build AI context, call
//                               OpenAI/Claude, return structured JSON.
// - VITE_MARKET_INSIGHTS_URL -> REST endpoint backed by the SQL aggregation
//                               views over PostgreSQL (jobs, skills, companies, roles).
// Leave either unset to keep running on local demo data.
const N8N_WEBHOOK_URL = import.meta.env.VITE_N8N_WEBHOOK_URL
const MARKET_INSIGHTS_URL = import.meta.env.VITE_MARKET_INSIGHTS_URL

const toArray = (value) => (Array.isArray(value) ? value : [])

const toSkillNames = (list) =>
  toArray(list).map((item) => (typeof item === 'string' ? item : item?.skill ?? item?.name ?? '')).filter(Boolean)

// Accepts either the exact contract or minor shape variations from the
// webhook response and normalizes it for the UI.
function normalizeAnalysis(raw) {
  return {
    matchScore: Math.max(0, Math.min(100, Number(raw?.matchScore ?? raw?.match_score ?? 0))),
    strengths: toSkillNames(raw?.strengths),
    missingSkills: toSkillNames(raw?.missingSkills ?? raw?.missing_skills ?? raw?.skillGap),
    roadmap: toArray(raw?.roadmap).map((step, idx) => ({
      phase: step?.phase ?? `Phase ${idx + 1}`,
      skill: step?.skill ?? step?.name ?? '',
      description: step?.description ?? '',
    })),
    recommendation: raw?.recommendation ?? raw?.aiRecommendation ?? '',
  }
}

function normalizeMarketInsights(raw) {
  return {
    updatedAt: raw?.updatedAt ?? null,
    topSkills: toArray(raw?.topSkills),
    topRoles: toArray(raw?.topRoles),
    topLocations: toArray(raw?.topLocations),
    trends: toArray(raw?.trends),
  }
}

export async function submitCareerAnalysis({ targetRole, currentSkills }) {
  if (!N8N_WEBHOOK_URL) {
    await new Promise((resolve) => setTimeout(resolve, 500))
    return { ...generateDemoAnalysis(targetRole, currentSkills), demo: true }
  }

  const response = await fetch(N8N_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ targetRole, currentSkills }),
  })

  if (!response.ok) {
    throw new Error(`Analysis request failed (${response.status})`)
  }

  return normalizeAnalysis(await response.json())
}

export async function fetchMarketInsights() {
  if (!MARKET_INSIGHTS_URL) {
    return { ...mockMarketInsights, demo: true }
  }

  const response = await fetch(MARKET_INSIGHTS_URL)

  if (!response.ok) {
    throw new Error(`Market insights request failed (${response.status})`)
  }

  return normalizeMarketInsights(await response.json())
}
