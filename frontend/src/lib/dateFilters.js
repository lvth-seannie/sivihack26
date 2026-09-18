// Tender cards carry two distinct business dates - published_at and
// submission_deadline (see App.css / TenderCard for how they're shown).
// This module is the single place that sorts/filters on them, so the
// "soonest first" and "within N days" definitions can't drift between the
// toolbar and the card's own urgency highlight.

const DAY_MS = 24 * 60 * 60 * 1000

function startOfToday() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

export function daysUntil(dateStr) {
  if (!dateStr) return null
  const target = new Date(dateStr)
  if (Number.isNaN(target.getTime())) return null
  return Math.round((target.getTime() - startOfToday().getTime()) / DAY_MS)
}

export function isDeadlineSoon(dateStr, withinDays = 7) {
  const days = daysUntil(dateStr)
  return days != null && days >= 0 && days <= withinDays
}

export function sortTenders(tenders, sortBy) {
  if (sortBy !== 'deadline') return tenders
  return [...tenders].sort((a, b) => {
    if (a.submission_deadline == null && b.submission_deadline == null) return 0
    if (a.submission_deadline == null) return 1
    if (b.submission_deadline == null) return -1
    return a.submission_deadline.localeCompare(b.submission_deadline)
  })
}

export const FILTER_PRESETS = ['all', 'publishedThisWeek', 'deadlineWithin7']

export function filterTenders(tenders, preset) {
  if (preset === 'publishedThisWeek') {
    return tenders.filter((t) => {
      const days = daysUntil(t.published_at)
      return days != null && days <= 0 && days >= -7
    })
  }
  if (preset === 'deadlineWithin7') {
    return tenders.filter((t) => isDeadlineSoon(t.submission_deadline))
  }
  return tenders
}
