import VerdictBadge from './VerdictBadge'
import CitationRow from './CitationRow'
import { useLanguage } from '../i18n/useLanguage'
import { formatCurrency } from '../lib/format'

// Lower rank = better verdict. Used only to pick which direction the
// mismatch callout should read - not a business ranking of the verdicts.
const VERDICT_RANK = { CANDIDATE: 0, FLAG: 1, HARD_FAIL: 2 }

export default function LotRow({ lot, tenderVerdict }) {
  const { locale, t, reasonText } = useLanguage()
  const isOpportunity = VERDICT_RANK[lot.verdict] < VERDICT_RANK[tenderVerdict]

  return (
    <li className={`lot-row${lot.differs_from_tender ? ' lot-row--differs' : ''}`}>
      <div className="lot-row__top">
        <span className="lot-row__label">
          {t('lotLabel', { n: lot.lot_number })}
          {lot.description ? ` — ${lot.description}` : ''}
        </span>
        <span className="lot-row__right">
          {lot.value != null && <span className="lot-row__value">{formatCurrency(lot.value, locale)}</span>}
          <VerdictBadge verdict={lot.verdict} small />
        </span>
      </div>

      {lot.differs_from_tender && (
        <p className="lot-row__flag-note">
          ⚠ {t(isOpportunity ? 'lotDiffersOpportunity' : 'lotDiffersCaution')}
        </p>
      )}

      <p className="lot-row__reason">{reasonText(lot.reason_code, lot.context)}</p>

      <CitationRow sourcePage={lot.source_page} />
    </li>
  )
}
