// Buckets tenders into the three verdict sections the UI renders. A tender's
// own verdict always places the full card (with all its lots nested inside).
// A lot whose verdict differs from its parent tender is ALSO lifted into its
// own section as a standalone card, so e.g. a CANDIDATE lot inside a
// HARD_FAIL tender surfaces in the Candidates section, not just buried in a
// collapsed Hard fails card.
export function buildSections(tenders = []) {
  const sections = { CANDIDATE: [], FLAG: [], HARD_FAIL: [] }

  for (const tender of tenders) {
    sections[tender.verdict]?.push({ kind: 'tender', tender })

    for (const lot of tender.lots ?? []) {
      if (lot.verdict !== tender.verdict) {
        sections[lot.verdict]?.push({ kind: 'lot', tender, lot })
      }
    }
  }

  return sections
}

// The single source of truth for "how many CANDIDATE/FLAG/HARD_FAIL items
// are there" - a tender counts once for its own verdict, plus one more for
// each lot whose verdict differs (bidding on that lot is a distinct action
// from bidding on the tender as a whole, so it's counted separately, same
// as it's shown separately). Anything that shows a count anywhere in the
// UI (summary pills, section headers) must derive it from this function so
// the numbers can't drift apart the way they did before.
export function countSections(tenders = []) {
  const sections = buildSections(tenders)
  return {
    CANDIDATE: sections.CANDIDATE.length,
    FLAG: sections.FLAG.length,
    HARD_FAIL: sections.HARD_FAIL.length,
  }
}
