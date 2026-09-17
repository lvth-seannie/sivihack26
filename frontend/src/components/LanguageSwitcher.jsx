import { LOCALES } from '../i18n/dictionaries'
import { useLanguage } from '../i18n/useLanguage'

const LABELS = { en: 'EN', de: 'DE', vi: 'VN' }

export default function LanguageSwitcher() {
  const { locale, setLocale, t } = useLanguage()

  return (
    <div className="lang-switcher" role="group" aria-label={t('languageLabel')}>
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          className={`lang-switcher__btn${code === locale ? ' is-active' : ''}`}
          onClick={() => setLocale(code)}
          aria-pressed={code === locale}
        >
          {LABELS[code]}
        </button>
      ))}
    </div>
  )
}
