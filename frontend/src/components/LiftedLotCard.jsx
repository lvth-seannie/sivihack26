import { useState } from 'react'
import VerdictBadge from './VerdictBadge'
import DetailPanel from './DetailPanel'
import { formatCurrency } from '../lib/format'

// A lot rendered as its own top-level card because its verdict differs from
// its parent tender's (e.g. a CANDIDATE lot inside an otherwise HARD_FAIL
// tender). Keeps the parent tender visible for context without hiding this
// exception inside a collapsed section.
export default function LiftedLotCard({ tender, lot }) {
  const [open, setOpen] = useState(false)
  const modifier = lot.verdict.toLowerCase().replace('_', '-')
  const hasDetail = Boolean(lot.source_snippet) || lot.source_page != null

  return (
    <article className={`tender-card tender-card--${modifier} tender-card--lifted`}>
      <div className="tender-card__top">
        <div className="tender-card__title-block">
          <p className="lifted-tag">
            Lot {lot.lot_number} thuộc gói thầu
            <VerdictBadge verdict={tender.verdict} small />
          </p>
          <h3>{tender.title}</h3>
          <p className="tender-card__meta">
            {lot.description || '—'} · {formatCurrency(lot.value)}
          </p>
          <p className="tender-card__reason">{lot.reason}</p>
        </div>
        <VerdictBadge verdict={lot.verdict} />
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

      {open && <DetailPanel sourceSnippet={lot.source_snippet} sourcePage={lot.source_page} />}
    </article>
  )
}
