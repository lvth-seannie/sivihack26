import { useState } from 'react'
import VerdictBadge from './VerdictBadge'
import DetailPanel from './DetailPanel'
import { formatCurrency } from '../lib/format'

export default function LotRow({ lot }) {
  const [open, setOpen] = useState(false)
  const hasDetail = Boolean(lot.source_snippet) || lot.source_page != null

  return (
    <li className={`lot-row${lot.differs_from_tender ? ' lot-row--differs' : ''}`}>
      <div className="lot-row__top">
        <span className="lot-row__label">
          Lot {lot.lot_number}
          {lot.description ? ` — ${lot.description}` : ''}
        </span>
        <span className="lot-row__right">
          {lot.value != null && <span className="lot-row__value">{formatCurrency(lot.value)}</span>}
          <VerdictBadge verdict={lot.verdict} small />
        </span>
      </div>

      {lot.differs_from_tender && (
        <p className="lot-row__flag-note">⚠ Khác với kết quả của gói thầu chính — đừng bỏ lỡ</p>
      )}

      <p className="lot-row__reason">{lot.reason}</p>

      {hasDetail && (
        <>
          <button className="detail-toggle" onClick={() => setOpen((o) => !o)}>
            {open ? 'Ẩn chi tiết nguồn' : 'Xem chi tiết nguồn'}
          </button>
          {open && <DetailPanel sourceSnippet={lot.source_snippet} sourcePage={lot.source_page} />}
        </>
      )}
    </li>
  )
}
