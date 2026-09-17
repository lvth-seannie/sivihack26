import { useLanguage } from '../i18n/useLanguage'

export default function ErrorAlert({ title, message, onRetry }) {
  const { t } = useLanguage()

  return (
    <div className="error-alert" role="alert">
      <span className="error-alert__icon" aria-hidden="true">
        !
      </span>
      <div className="error-alert__body">
        {title && <p className="error-alert__title">{title}</p>}
        <p className="error-alert__message">{message}</p>
      </div>
      {onRetry && (
        <button className="error-alert__retry" onClick={onRetry}>
          {t('retry')}
        </button>
      )}
    </div>
  )
}
