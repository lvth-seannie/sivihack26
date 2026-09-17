import VerdictBadge from './VerdictBadge'
import CitationRow from './CitationRow'
import { useLanguage } from '../i18n/useLanguage'
import { formatCurrency } from '../lib/format'

export default function LotRow({ lot }) {
  const { locale, t, reasonText } = useLanguage()

  return (
    <li className={`lot-row${lot.differs_from_tender ? ' lot-row--differs' : ''}`}>
      <div className="lot-row__top">
        <span className="lot-row__label">
          {t('lotLabel', { n: lot.lot_number })}
          {lot.description ? ` — ${lot.description}` : ''}
        </span>
        <span className="lot-row__right">
          {lot.value != null && <span className="lot-row__value">{formatCurrency(lot.value, locale)}</span>}
          <VerdictBadge verdict={lot.verdict} small />
        </span>
      </div>

      {lot.differs_from_tender && <p className="lot-row__flag-note">⚠ {t('lotDiffersWarning')}</p>}

      <p className="lot-row__reason">{reasonText(lot.reason_code, lot.context)}</p>

      <CitationRow sourcePage={lot.source_page} />
    </li>
  )
}
