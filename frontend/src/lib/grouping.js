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
