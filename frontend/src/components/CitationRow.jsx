import { useLanguage } from '../i18n/useLanguage'

export default function CitationRow({ sourcePage, sourceUrl, sourceIsCached }) {
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
      {sourceUrl && !sourceIsCached && (
        <span className="citation-row__caveat">{t('sourceStaleCaveat')}</span>
      )}
    </div>
  )
}
