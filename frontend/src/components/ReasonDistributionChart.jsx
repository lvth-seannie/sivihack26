import { useMemo } from 'react'
import { useLanguage } from '../i18n/useLanguage'
import { HARD_FAIL_CATEGORY_KEYS, hardFailReasonCounts } from '../lib/reasonCategories'

// Plain CSS bars, not a charting library - this is one simple breakdown
// (hard-fail count per reason category), recomputed whenever the company
// or the source-available filter changes, to make the distribution shift
// between companies ("the swap test") visible at a glance.
export default function ReasonDistributionChart({ tenders, sourceAvailableOnly }) {
  const { t } = useLanguage()

  const counts = useMemo(
    () => hardFailReasonCounts(tenders, { sourceAvailableOnly }),
    [tenders, sourceAvailableOnly],
  )
  const total = HARD_FAIL_CATEGORY_KEYS.reduce((sum, key) => sum + counts[key], 0)
  const max = Math.max(1, ...HARD_FAIL_CATEGORY_KEYS.map((key) => counts[key]))

  if (total === 0) return null

  return (
    <div className="reason-chart">
      <h3 className="reason-chart__title">{t('reasonChartTitle')}</h3>
      <div className="reason-chart__bars">
        {HARD_FAIL_CATEGORY_KEYS.map((key) => (
          <div className="reason-chart__row" key={key}>
            <span className="reason-chart__label">{t(`reasonCategory_${key}`)}</span>
            <div className="reason-chart__track">
              <div className="reason-chart__fill" style={{ width: `${(counts[key] / max) * 100}%` }} />
            </div>
            <span className="reason-chart__count">{counts[key]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
