import VerdictBadge from './VerdictBadge'
import CitationRow from './CitationRow'
import LotRow from './LotRow'
import { useLanguage } from '../i18n/useLanguage'
import { formatCurrency } from '../lib/format'

export default function TenderCard({ tender }) {
  const { locale, reasonText } = useLanguage()
  const modifier = tender.verdict.toLowerCase().replace('_', '-')

  return (
    <article className={`tender-card tender-card--${modifier}`}>
      <div className="tender-card__top">
        <div className="tender-card__title-block">
          <h3>{tender.title}</h3>
          <p className="tender-card__meta">
            {tender.location || '—'} · {formatCurrency(tender.contract_value, locale)}
          </p>
          <p className="tender-card__reason">{reasonText(tender.reason_code, tender.context)}</p>
        </div>
        <VerdictBadge verdict={tender.verdict} />
      </div>

      <CitationRow sourcePage={tender.source_page} sourceUrl={tender.source_url} />

      {tender.lots.length > 0 && (
        <ul className="lot-list">
          {tender.lots.map((lot) => (
            <LotRow key={lot.id} lot={lot} />
          ))}
        </ul>
      )}
    </article>
  )
}
