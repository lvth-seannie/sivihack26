import { useMemo, useState } from 'react'
import TenderCard from './TenderCard'
import LiftedLotCard from './LiftedLotCard'
import { buildSections } from '../lib/grouping'
import { FILTER_PRESETS, filterTenders, sortTenders } from '../lib/dateFilters'
import { useLanguage } from '../i18n/useLanguage'

const SECTIONS = [
  { key: 'CANDIDATE', titleKey: 'sectionCandidatesTitle', descKey: 'sectionCandidatesDesc', defaultOpen: true },
  { key: 'FLAG', titleKey: 'sectionFlagsTitle', descKey: 'sectionFlagsDesc', defaultOpen: true },
  { key: 'HARD_FAIL', titleKey: 'sectionHardFailsTitle', descKey: 'sectionHardFailsDesc', defaultOpen: false },
]

export default function ResultsBoard({ tenders }) {
  const { t } = useLanguage()
  const [sortBy, setSortBy] = useState('default')
  const [filterPreset, setFilterPreset] = useState('all')

  const visibleTenders = useMemo(
    () => sortTenders(filterTenders(tenders, filterPreset), sortBy),
    [tenders, filterPreset, sortBy],
  )
  const sections = useMemo(() => buildSections(visibleTenders), [visibleTenders])

  return (
    <div className="results-board">
      <div className="results-toolbar">
        <label className="results-toolbar__field">
          <span>{t('sortLabel')}</span>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="default">{t('sortDefault')}</option>
            <option value="deadline">{t('sortDeadlineSoonest')}</option>
          </select>
        </label>

        <div className="results-toolbar__presets">
          {FILTER_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              className={`filter-chip${filterPreset === preset ? ' is-active' : ''}`}
              onClick={() => setFilterPreset(preset)}
            >
              {t(`filterPreset_${preset}`)}
            </button>
          ))}
        </div>
      </div>

      {SECTIONS.map((cfg) => (
        <Section key={cfg.key} cfg={cfg} items={sections[cfg.key]} />
      ))}
    </div>
  )
}

function Section({ cfg, items }) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(cfg.defaultOpen)
  const modifier = cfg.key.toLowerCase().replace('_', '-')

  return (
    <section className={`result-section result-section--${modifier}`}>
      <button className="result-section__header" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="result-section__dot" />
        <h2>{t(cfg.titleKey)}</h2>
        <span className="result-section__count">{items.length}</span>
        <span className="result-section__desc">{t(cfg.descKey)}</span>
        <span className={`result-section__chevron${open ? ' is-open' : ''}`}>⌄</span>
      </button>

      {open && (
        <div className="result-section__body">
          {items.length === 0 ? (
            <p className="result-section__empty">{t('sectionEmpty')}</p>
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
