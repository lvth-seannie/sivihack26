// Local stand-in for the n8n pipeline (validate -> query PostgreSQL -> calculate
// skill gap -> build AI context -> OpenAI/Claude -> structured JSON) so the
// Career Advisor flow works end-to-end before the webhook is wired up.
// The shape returned here is exactly what src/services/api.js expects back
// from VITE_N8N_WEBHOOK_URL, so switching to the real backend requires no UI changes.
const ROLE_REQUIRED_SKILLS = {
  'Data Analyst': ['SQL', 'Excel', 'Python', 'Tableau', 'Statistics'],
  'Data Engineer': ['Python', 'SQL', 'Spark', 'Airflow', 'AWS', 'Docker'],
  'Business Analyst': ['SQL', 'Excel', 'Power BI', 'Stakeholder Management', 'Statistics'],
  'Software Engineer': ['JavaScript', 'React', 'Node.js', 'SQL', 'Git', 'REST API'],
  'Product Manager': ['Roadmapping', 'SQL', 'Stakeholder Management', 'Agile', 'Analytics'],
}

const norm = (skill) => skill.trim().toLowerCase()

export function generateDemoAnalysis(targetRole, currentSkills) {
  const required = ROLE_REQUIRED_SKILLS[targetRole] || ROLE_REQUIRED_SKILLS['Data Engineer']
  const owned = new Set(currentSkills.map(norm))

  const strengths = required.filter((skill) => owned.has(norm(skill)))
  const missingSkills = required.filter((skill) => !owned.has(norm(skill)))
  const matchScore = Math.round((strengths.length / required.length) * 100)

  const roadmap = missingSkills.map((skill, idx) => ({
    phase: `Phase ${idx + 1}`,
    skill,
    description: `Build working proficiency in ${skill} through a focused project or course.`,
  }))

  const recommendation = missingSkills.length
    ? `You already cover ${strengths.length} of ${required.length} core skills for ${targetRole}. Focus next on ${missingSkills.slice(0, 2).join(' and ')} to close the biggest gap and become competitive for this role within 3-6 months.`
    : `You already meet every core skill requirement for ${targetRole}. Consider targeting senior-level or specialized openings to stand out further.`

  return { matchScore, strengths, missingSkills, roadmap, recommendation }
}
