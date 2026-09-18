import { useMemo, useState } from 'react'
import TenderCard from './TenderCard'
import LiftedLotCard from './LiftedLotCard'
import ReasonDistributionChart from './ReasonDistributionChart'
import { buildSections } from '../lib/grouping'
import { FILTER_PRESETS, filterTenders, sortTenders } from '../lib/dateFilters'
import { availableReasonCategories, categoryFor } from '../lib/reasonCategories'
import { useLanguage } from '../i18n/useLanguage'

const SECTIONS = [
  { key: 'CANDIDATE', titleKey: 'sectionCandidatesTitle', descKey: 'sectionCandidatesDesc', defaultOpen: true },
  { key: 'FLAG', titleKey: 'sectionFlagsTitle', descKey: 'sectionFlagsDesc', defaultOpen: true },
  { key: 'HARD_FAIL', titleKey: 'sectionHardFailsTitle', descKey: 'sectionHardFailsDesc', defaultOpen: false },
]

const VERDICT_LABEL_KEYS = {
  CANDIDATE: 'verdictToggle_CANDIDATE',
  FLAG: 'verdictToggle_FLAG',
  HARD_FAIL: 'verdictToggle_HARD_FAIL',
}

function itemReasonCode(item) {
  return item.kind === 'tender' ? item.tender.reason_code : item.lot.reason_code
}

export default function ResultsBoard({ tenders }) {
  const { t } = useLanguage()
  const [sortBy, setSortBy] = useState('default')
  const [filterPreset, setFilterPreset] = useState('all')
  const [reasonCategory, setReasonCategory] = useState('all')
  const [sourceAvailableOnly, setSourceAvailableOnly] = useState(false)
  const [verdictVisible, setVerdictVisible] = useState({ CANDIDATE: true, FLAG: true, HARD_FAIL: true })

  const reasonOptions = useMemo(() => availableReasonCategories(tenders), [tenders])

  const visibleTenders = useMemo(
    () => sortTenders(filterTenders(tenders, filterPreset), sortBy),
    [tenders, filterPreset, sortBy],
  )

  const sections = useMemo(() => {
    const raw = buildSections(visibleTenders)
    const filtered = {}
    for (const key of Object.keys(raw)) {
      filtered[key] = raw[key].filter((item) => {
        if (reasonCategory !== 'all' && categoryFor(itemReasonCode(item)) !== reasonCategory) return false
        if (sourceAvailableOnly && !item.tender.source_is_cached) return false
        return true
      })
    }
    return filtered
  }, [visibleTenders, reasonCategory, sourceAvailableOnly])

  const anyFilterActive = filterPreset !== 'all' || reasonCategory !== 'all' || sourceAvailableOnly

  return (
    <div className="results-board">
      <ReasonDistributionChart tenders={tenders} sourceAvailableOnly={sourceAvailableOnly} />

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

      <div className="results-toolbar">
        <div className="results-toolbar__presets" role="group" aria-label={t('verdictToggleLabel')}>
          {SECTIONS.map((cfg) => (
            <button
              key={cfg.key}
              type="button"
              className={`filter-chip${verdictVisible[cfg.key] ? ' is-active' : ''}`}
              onClick={() => setVerdictVisible((v) => ({ ...v, [cfg.key]: !v[cfg.key] }))}
            >
              {t(VERDICT_LABEL_KEYS[cfg.key])}
            </button>
          ))}
        </div>

        {reasonOptions.length > 0 && (
          <label className="results-toolbar__field">
            <span>{t('reasonTypeLabel')}</span>
            <select value={reasonCategory} onChange={(e) => setReasonCategory(e.target.value)}>
              <option value="all">{t('filterPreset_all')}</option>
              {reasonOptions.map((key) => (
                <option key={key} value={key}>
                  {t(`reasonCategory_${key}`)}
                </option>
              ))}
            </select>
          </label>
        )}

        <button
          type="button"
          className={`filter-chip${sourceAvailableOnly ? ' is-active' : ''}`}
          onClick={() => setSourceAvailableOnly((v) => !v)}
        >
          {t('sourceAvailableLabel')}
        </button>
      </div>

      {SECTIONS.filter((cfg) => verdictVisible[cfg.key]).map((cfg) => (
        <Section key={cfg.key} cfg={cfg} items={sections[cfg.key]} anyFilterActive={anyFilterActive} />
      ))}
    </div>
  )
}

function Section({ cfg, items, anyFilterActive }) {
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
            <p className="result-section__empty">{anyFilterActive ? t('sectionEmptyFiltered') : t('sectionEmpty')}</p>
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
