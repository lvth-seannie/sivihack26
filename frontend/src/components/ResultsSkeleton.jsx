import { useLanguage } from '../i18n/useLanguage'

const COLUMNS = [
  { key: 'candidate', cards: 3 },
  { key: 'flag', cards: 2 },
  { key: 'hard-fail', cards: 2 },
]

export default function ResultsSkeleton() {
  const { t } = useLanguage()

  return (
    <div className="skeleton-board" role="status" aria-label={t('loadingResultsLabel')}>
      {COLUMNS.map((col) => (
        <div key={col.key} className={`skeleton-section skeleton-section--${col.key}`}>
          <div className="skeleton-section__header">
            <span className="skeleton-dot" />
            <span className="skeleton-bar skeleton-bar--title" />
            <span className="skeleton-bar skeleton-bar--count" />
          </div>
          {Array.from({ length: col.cards }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <span className="skeleton-bar skeleton-bar--line-lg" />
              <span className="skeleton-bar skeleton-bar--line-sm" />
              <span className="skeleton-bar skeleton-bar--line-md" />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
