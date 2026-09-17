import { formatCurrency, formatKm } from '../lib/format'

const L = 'en'

export default {
  ui: {
    appTitle: 'Tender AI Screening',
    appSubtitle: 'Deterministic rule engine — no LLM in the loop',
    heroSubtitle: 'Select a company profile, then screen it against every open tender.',
    companyLabel: 'Company',
    screenButton: 'Screen tenders',
    screeningButton: 'Screening…',
    loadingCompanies: 'Loading companies…',
    loading: 'Loading…',
    companyLoadError: 'Could not load companies. Check the backend connection.',
    companyLoadErrorTitle: 'Connection problem',
    screenError: 'Screening failed. Please try again.',
    retry: 'Retry',
    loadingResultsLabel: 'Loading results…',
    updatedAt: 'Updated {time}',
    chipCandidates: '{n} candidates',
    chipFlags: '{n} flags',
    chipHardFails: '{n} hard fails',
    emptyStateText: 'No screening results yet for this company.',
    sectionCandidatesTitle: 'Candidates',
    sectionCandidatesDesc: 'Meets all requirements — worth bidding',
    sectionFlagsTitle: 'Flags',
    sectionFlagsDesc: 'Passes, but needs a closer look',
    sectionHardFailsTitle: 'Hard fails',
    sectionHardFailsDesc: 'Fails a knockout rule',
    sectionEmpty: 'Nothing in this section.',
    viewSource: 'View source detail',
    hideSource: 'Hide source detail',
    sourceLink: 'Source ↗',
    pageLabel: 'Page {n}',
    lotDiffersWarning: "Differs from the tender's own result — don't miss this",
    lotLabel: 'Lot {n}',
    lotOfTender: 'Lot {n} of tender',
    tenderParentVerdict: 'Tender result',
    profileTitle: 'Company profile',
    profileToggleShow: 'Show company profile',
    profileToggleHide: 'Hide company profile',
    profileFounded: 'Founded',
    profileEmployees: 'Employees',
    profileRevenue: 'Revenue',
    profileHq: 'Headquarters',
    profileRadius: 'Operating radius',
    profileContractRange: 'Contract size',
    profileGuaranteeCeiling: 'Guarantee ceiling',
    profileAvailableFrom: 'Available from',
    profileCanShow: 'Can show',
    profileCannotShow: 'Cannot show',
    languageLabel: 'Language',
    verdictCandidate: 'Candidate',
    verdictFlag: 'Flag',
    verdictHardFail: 'Hard fail',
  },
  reasons: {
    OUT_OF_RADIUS: (ctx) =>
      `${formatKm(ctx.distance_km, L)} exceeds the ${formatKm(ctx.radius_km, L)} operating radius.`,
    OUT_OF_VALUE_RANGE: (ctx) =>
      `${formatCurrency(ctx.value, L)} is outside the ${formatCurrency(ctx.min, L)}–${formatCurrency(ctx.max, L)} range this company bids.`,
    GUARANTEE_OVER_CEILING: (ctx) =>
      `Required guarantee ${formatCurrency(ctx.guarantee_required, L)} exceeds the ${formatCurrency(ctx.ceiling, L)} ceiling.`,
    MISSING_REFERENCES: (ctx) =>
      `Missing required reference${ctx.missing.length > 1 ? 's' : ''}: ${ctx.missing.join(', ')}.`,
    CAPABILITY_EXCLUDED: (ctx) =>
      `Requires an excluded capability: ${ctx.excluded.join(', ')}.`,
    GUARANTEE_NEAR_CEILING: (ctx) =>
      `Required guarantee ${formatCurrency(ctx.guarantee_required, L)} is ${ctx.ratio_pct}% of the ${formatCurrency(ctx.ceiling, L)} ceiling.`,
    CANDIDATE_OK: () => 'Meets radius, contract value, guarantee and reference requirements.',
  },
}
