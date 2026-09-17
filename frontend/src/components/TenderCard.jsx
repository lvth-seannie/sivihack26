import { useState } from 'react'
import VerdictBadge from './VerdictBadge'
import DetailPanel from './DetailPanel'
import LotRow from './LotRow'
import { formatCurrency } from '../lib/format'

export default function TenderCard({ tender }) {
  const [open, setOpen] = useState(false)
  const modifier = tender.verdict.toLowerCase().replace('_', '-')
  const hasDetail = Boolean(tender.source_snippet) || tender.source_page != null

  return (
    <article className={`tender-card tender-card--${modifier}`}>
      <div className="tender-card__top">
        <div className="tender-card__title-block">
          <h3>{tender.title}</h3>
          <p className="tender-card__meta">
            {tender.location || '—'} · {formatCurrency(tender.contract_value)}
          </p>
          <p className="tender-card__reason">{tender.reason}</p>
        </div>
        <VerdictBadge verdict={tender.verdict} />
      </div>

      <div className="tender-card__actions">
        {hasDetail && (
          <button className="detail-toggle" onClick={() => setOpen((o) => !o)}>
            {open ? 'Ẩn chi tiết nguồn' : 'Xem chi tiết nguồn'}
          </button>
        )}
        {tender.source_url && (
          <a className="tender-card__link" href={tender.source_url} target="_blank" rel="noreferrer">
            Nguồn ↗
          </a>
        )}
      </div>

      {open && (
        <DetailPanel
          sourceSnippet={tender.source_snippet}
          sourcePage={tender.source_page}
        />
      )}

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
