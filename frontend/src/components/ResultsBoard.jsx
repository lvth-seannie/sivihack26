import { useMemo, useState } from 'react'
import TenderCard from './TenderCard'
import LiftedLotCard from './LiftedLotCard'
import { buildSections } from '../lib/grouping'

const SECTIONS = [
  {
    key: 'CANDIDATE',
    title: 'Candidates',
    description: 'Đáp ứng đủ điều kiện — nên đấu thầu',
    defaultOpen: true,
  },
  {
    key: 'FLAG',
    title: 'Flags',
    description: 'Đạt điều kiện nhưng cần lưu ý',
    defaultOpen: true,
  },
  {
    key: 'HARD_FAIL',
    title: 'Hard fails',
    description: 'Không đạt điều kiện knockout',
    defaultOpen: false,
  },
]

export default function ResultsBoard({ tenders }) {
  const sections = useMemo(() => buildSections(tenders), [tenders])

  return (
    <div className="results-board">
      {SECTIONS.map((cfg) => (
        <Section key={cfg.key} cfg={cfg} items={sections[cfg.key]} />
      ))}
    </div>
  )
}

function Section({ cfg, items }) {
  const [open, setOpen] = useState(cfg.defaultOpen)
  const modifier = cfg.key.toLowerCase().replace('_', '-')

  return (
    <section className={`result-section result-section--${modifier}`}>
      <button className="result-section__header" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="result-section__dot" />
        <h2>{cfg.title}</h2>
        <span className="result-section__count">{items.length}</span>
        <span className="result-section__desc">{cfg.description}</span>
        <span className={`result-section__chevron${open ? ' is-open' : ''}`}>⌄</span>
      </button>

      {open && (
        <div className="result-section__body">
          {items.length === 0 ? (
            <p className="result-section__empty">Không có mục nào trong mục này.</p>
          ) : (
            items.map((item) =>
              item.kind === 'tender' ? (
                <TenderCard key={`t-${item.tender.id}`} tender={item.tender} />
              ) : (
                <LiftedLotCard key={`l-${item.tender.id}-${item.lot.id}`} tender={item.tender} lot={item.lot} />
              ),
            )
          )}
        </div>
      )}
    </section>
  )
}
