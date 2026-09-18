import { formatCurrency, formatKm } from '../lib/format'

const L = 'de'

export default {
  ui: {
    appTitle: 'Ausschreibungs-Screening',
    appSubtitle: 'Deterministische Regel-Engine — keine KI im Entscheidungspfad',
    heroSubtitle: 'Unternehmen auswählen und gegen alle offenen Ausschreibungen prüfen.',
    companyLabel: 'Unternehmen',
    screenButton: 'Ausschreibungen prüfen',
    screeningButton: 'Wird geprüft…',
    loadingCompanies: 'Unternehmen werden geladen…',
    loading: 'Wird geladen…',
    companyLoadError: 'Unternehmen konnten nicht geladen werden. Backend-Verbindung prüfen.',
    companyLoadErrorTitle: 'Verbindungsproblem',
    screenError: 'Prüfung fehlgeschlagen. Bitte erneut versuchen.',
    retry: 'Erneut versuchen',
    loadingResultsLabel: 'Ergebnisse werden geladen…',
    updatedAt: 'Aktualisiert {time}',
    chipCandidates: '{n} Kandidaten',
    chipFlags: '{n} Hinweise',
    chipHardFails: '{n} Ausschlüsse',
    emptyStateText: 'Für dieses Unternehmen liegen noch keine Prüfergebnisse vor.',
    sectionCandidatesTitle: 'Kandidaten',
    sectionCandidatesDesc: 'Erfüllt alle Anforderungen — Angebot lohnt sich',
    sectionFlagsTitle: 'Hinweise',
    sectionFlagsDesc: 'Besteht die Prüfung, aber genauer hinsehen',
    sectionHardFailsTitle: 'Ausschlüsse',
    sectionHardFailsDesc: 'Scheitert an einem Ausschlusskriterium',
    sectionEmpty: 'Kein Eintrag in diesem Bereich.',
    viewSource: 'Quellenangabe anzeigen',
    hideSource: 'Quellenangabe ausblenden',
    sourceLink: 'Quelle ↗',
    pageLabel: 'Seite {n}',
    lotDiffersWarning: 'Weicht vom Ergebnis der Hauptausschreibung ab — nicht übersehen',
    lotLabel: 'Los {n}',
    lotOfTender: 'Los {n} der Ausschreibung',
    tenderParentVerdict: 'Ergebnis der Ausschreibung',
    profileTitle: 'Unternehmensprofil',
    profileToggleShow: 'Unternehmensprofil anzeigen',
    profileToggleHide: 'Unternehmensprofil ausblenden',
    profileFounded: 'Gegründet',
    profileEmployees: 'Mitarbeiter',
    profileRevenue: 'Umsatz',
    profileHq: 'Sitz',
    profileRadius: 'Einsatzradius',
    profileContractRange: 'Auftragsgröße',
    profileGuaranteeCeiling: 'Bürgschaftslimit',
    profileWeeklyBidCapacity: 'Angebotskapazität',
    profileWeeklyBidCapacityValue: '{n} Ausschreibungen / Woche',
    profileAvailableFrom: 'Verfügbar ab',
    profileCanShow: 'Referenzen',
    profileCannotShow: 'Nicht leistbar',
    languageLabel: 'Sprache',
    verdictCandidate: 'Kandidat',
    verdictFlag: 'Hinweis',
    verdictHardFail: 'Ausschluss',
    citationWithPage: '(siehe S. {page}: „{snippet}“)',
    citationNoPage: '(Quelle: „{snippet}“)',
  },
  reasons: {
    OUT_OF_RADIUS: (ctx) =>
      `${formatKm(ctx.distance_km, L)} liegen außerhalb des Einsatzradius von ${formatKm(ctx.radius_km, L)}.`,
    OUT_OF_VALUE_RANGE: (ctx) =>
      `${formatCurrency(ctx.value, L)} liegt außerhalb der Auftragsgröße von ${formatCurrency(ctx.min, L)}–${formatCurrency(ctx.max, L)}, die dieses Unternehmen anbietet.`,
    GUARANTEE_OVER_CEILING: (ctx) =>
      `Geforderte Bürgschaft ${formatCurrency(ctx.guarantee_required, L)} übersteigt das Limit von ${formatCurrency(ctx.ceiling, L)}.`,
    MISSING_REFERENCES: (ctx) =>
      `Fehlende geforderte Referenz${ctx.missing.length > 1 ? 'en' : ''}: ${ctx.missing.join(', ')}.`,
    CAPABILITY_EXCLUDED: (ctx) =>
      `Erfordert eine ausgeschlossene Leistung: ${ctx.excluded.join(', ')}.`,
    GUARANTEE_NEAR_CEILING: (ctx) =>
      `Geforderte Bürgschaft ${formatCurrency(ctx.guarantee_required, L)} entspricht ${ctx.ratio_pct}% des Limits von ${formatCurrency(ctx.ceiling, L)}.`,
    LOCATION_UNVERIFIED: () =>
      'Standort konnte nicht überprüft werden — manuelle Prüfung erforderlich.',
    PENDING_EXTRACTION: () =>
      'Diese Ausschreibung wurde noch nicht ausgewertet — Bürgschaft, Referenzen und Auftragswert sind ungeprüft. Manuelle Prüfung erforderlich.',
    CANDIDATE_OK: () =>
      'Erfüllt Einsatzradius, Auftragswert, Bürgschaftslimit und geforderte Referenzen.',
  },
}
