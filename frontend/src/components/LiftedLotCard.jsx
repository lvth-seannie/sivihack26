import VerdictBadge from './VerdictBadge'
import CitationRow from './CitationRow'
import { useLanguage } from '../i18n/useLanguage'
import { formatCurrency } from '../lib/format'

// A lot rendered as its own top-level card because its verdict differs from
// its parent tender's (e.g. a CANDIDATE lot inside an otherwise HARD_FAIL
// tender). Keeps the parent tender visible for context without hiding this
// exception inside a collapsed section.
export default function LiftedLotCard({ tender, lot }) {
  const { locale, t, reasonText } = useLanguage()
  const modifier = lot.verdict.toLowerCase().replace('_', '-')

  return (
    <article className={`tender-card tender-card--${modifier} tender-card--lifted`}>
      <div className="tender-card__top">
        <div className="tender-card__title-block">
          <p className="lifted-tag">
            {t('lotOfTender', { n: lot.lot_number })}
            <VerdictBadge verdict={tender.verdict} small />
          </p>
          <h3>{tender.title}</h3>
          <p className="tender-card__meta">
            {lot.description || '—'} · {formatCurrency(lot.value, locale)}
          </p>
          <p className="tender-card__reason">{reasonText(lot.reason_code, lot.context)}</p>
        </div>
        <VerdictBadge verdict={lot.verdict} />
      </div>

      <CitationRow sourcePage={lot.source_page} sourceUrl={tender.source_url} />
    </article>
  )
}
