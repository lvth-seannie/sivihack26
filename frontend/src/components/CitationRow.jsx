import { useLanguage } from '../i18n/useLanguage'

export default function CitationRow({ sourcePage, sourceUrl }) {
  const { t } = useLanguage()
  if (sourcePage == null && !sourceUrl) return null

  return (
    <div className="citation-row">
      {sourcePage != null && <span className="citation-row__page">{t('pageLabel', { n: sourcePage })}</span>}
      {sourceUrl && (
        <a href={sourceUrl} target="_blank" rel="noreferrer">
          {t('sourceLink')}
        </a>
      )}
    </div>
  )
}
