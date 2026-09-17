import { useLanguage } from '../i18n/useLanguage'

export default function EmptyState({ onScreen, loading }) {
  const { t } = useLanguage()
  return (
    <div className="empty-state">
      <p>{t('emptyStateText')}</p>
      <button className="btn-primary" onClick={onScreen} disabled={loading}>
        {loading ? t('screeningButton') : t('screenButton')}
      </button>
    </div>
  )
}
