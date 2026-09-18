import { useLanguage } from '../i18n/useLanguage'
import { formatDate } from '../lib/format'
import { isDeadlineSoon } from '../lib/dateFilters'

// published_at and submission_deadline are two distinct business dates -
// never extracted_at, which is internal pipeline metadata. Either can be
// null (not every source/notice carries both), in which case that half is
// simply omitted rather than shown as a placeholder.
export default function TenderDates({ publishedAt, submissionDeadline }) {
  const { locale, t } = useLanguage()
  if (!publishedAt && !submissionDeadline) return null

  const deadlineSoon = isDeadlineSoon(submissionDeadline)

  return (
    <p className="tender-card__dates">
      {publishedAt && <span className="tender-card__date">{t('publishedLabel', { date: formatDate(publishedAt, locale) })}</span>}
      {submissionDeadline && (
        <span className={`tender-card__date${deadlineSoon ? ' tender-card__date--soon' : ''}`}>
          {t('deadlineLabel', { date: formatDate(submissionDeadline, locale) })}
        </span>
      )}
    </p>
  )
}
