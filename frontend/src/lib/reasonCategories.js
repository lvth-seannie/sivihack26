// Groups the engine's stable reason_code strings (see backend/api/engine.py)
// into the handful of categories a human filter/chart cares about. A HARD
// FAIL only ever carries one reason_code per category below (e.g.
// GUARANTEE_NEAR_CEILING is a FLAG, never a HARD_FAIL, so "guarantee" maps
// 1:1 to GUARANTEE_OVER_CEILING there) - the grouping only actually merges
// codes when both a FLAG and a HARD_FAIL variant of the same concern exist.
export const REASON_CATEGORIES = {
  distance: ['OUT_OF_RADIUS', 'LOCATION_UNVERIFIED'],
  value: ['OUT_OF_VALUE_RANGE'],
  guarantee: ['GUARANTEE_OVER_CEILING', 'GUARANTEE_NEAR_CEILING'],
  references: ['MISSING_REFERENCES'],
  capability: ['CAPABILITY_EXCLUDED'],
  extraction: ['PENDING_EXTRACTION'],
}

export const CATEGORY_KEYS = Object.keys(REASON_CATEGORIES)

// HARD_FAIL-only categories, in the order the distribution chart shows
// them - CANDIDATE_OK and the FLAG-only categories never appear there.
export const HARD_FAIL_CATEGORY_KEYS = ['distance', 'value', 'guarantee', 'references', 'capability']

const REASON_TO_CATEGORY = Object.fromEntries(
  Object.entries(REASON_CATEGORIES).flatMap(([category, codes]) => codes.map((code) => [code, category])),
)

export function categoryFor(reasonCode) {
  return REASON_TO_CATEGORY[reasonCode] ?? null
}

// Flattens tenders into the same {kind, tender, lot?} items buildSections()
// groups into sections - a tender counts once for its own reason_code, plus
// once more for each lot whose verdict differs from its parent's (same
// "distinct actionable item" rule used everywhere else in this UI).
export function iterReasonItems(tenders = []) {
  const items = []
  for (const tender of tenders) {
    items.push({ kind: 'tender', tender, lot: null, reasonCode: tender.reason_code, verdict: tender.verdict })
    for (const lot of tender.lots ?? []) {
      if (lot.verdict !== tender.verdict) {
        items.push({ kind: 'lot', tender, lot, reasonCode: lot.reason_code, verdict: lot.verdict })
      }
    }
  }
  return items
}

// Which reason-type filter chips make sense for this company's current
// result set - never hardcoded, so a company with no CAPABILITY_EXCLUDED
// items simply doesn't get a "Capability" chip.
export function availableReasonCategories(tenders) {
  const present = new Set()
  for (const item of iterReasonItems(tenders)) {
    const category = categoryFor(item.reasonCode)
    if (category) present.add(category)
  }
  return CATEGORY_KEYS.filter((key) => present.has(key))
}

// source_is_cached is the exact same flag the "Nguồn" link already uses to
// decide between our B2 copy and the external URL (see services.py's
// _resolve_source) - reused here rather than recomputed, per the task.
export function hardFailReasonCounts(tenders, { sourceAvailableOnly = false } = {}) {
  const counts = Object.fromEntries(HARD_FAIL_CATEGORY_KEYS.map((key) => [key, 0]))
  for (const item of iterReasonItems(tenders)) {
    if (item.verdict !== 'HARD_FAIL') continue
    if (sourceAvailableOnly && !item.tender.source_is_cached) continue
    const category = categoryFor(item.reasonCode)
    if (category && category in counts) counts[category] += 1
  }
  return counts
}
