import { useState } from 'react'
import { useLanguage } from '../i18n/useLanguage'
import { formatCurrency, formatDate, formatKm, formatNumber } from '../lib/format'

export default function CompanyProfile({ company }) {
  const { locale, t } = useLanguage()
  const [open, setOpen] = useState(false)

  const stats = [
    company.founded_year != null && { label: t('profileFounded'), value: company.founded_year },
    company.employee_count != null && { label: t('profileEmployees'), value: formatNumber(company.employee_count, locale) },
    company.revenue_eur != null && { label: t('profileRevenue'), value: `≈ ${formatCurrency(company.revenue_eur, locale)}` },
    { label: t('profileHq'), value: company.region_center },
    { label: t('profileRadius'), value: formatKm(company.region_radius_km, locale) },
    { label: t('profileContractRange'), value: `${formatCurrency(company.contract_min, locale)} – ${formatCurrency(company.contract_max, locale)}` },
    company.guarantee_ceiling != null && { label: t('profileGuaranteeCeiling'), value: formatCurrency(company.guarantee_ceiling, locale) },
    company.weekly_bid_capacity != null && {
      label: t('profileWeeklyBidCapacity'),
      value: t('profileWeeklyBidCapacityValue', { n: company.weekly_bid_capacity }),
    },
    company.available_from && { label: t('profileAvailableFrom'), value: formatDate(company.available_from, locale) },
  ].filter(Boolean)

  return (
    <section className="company-profile">
      <button className="company-profile__toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="company-profile__name">{company.name}</span>
        <span className="company-profile__toggle-label">
          {open ? t('profileToggleHide') : t('profileToggleShow')}
        </span>
        <span className={`result-section__chevron${open ? ' is-open' : ''}`}>⌄</span>
      </button>

      {open && (
        <div className="company-profile__body">
          {company.description && <p className="company-profile__description">{company.description}</p>}
          {company.tagline && <blockquote className="company-profile__tagline">&ldquo;{company.tagline}&rdquo;</blockquote>}

          <div className="company-profile__stats">
            {stats.map((s) => (
              <div key={s.label} className="company-profile__stat">
                <span className="company-profile__stat-label">{s.label}</span>
                <span className="company-profile__stat-value">{s.value}</span>
              </div>
            ))}
          </div>

          <div className="company-profile__lists">
            {company.can_show.length > 0 && (
              <div className="company-profile__list company-profile__list--can">
                <h4>{t('profileCanShow')}</h4>
                <ul>
                  {company.can_show.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {company.cannot_show.length > 0 && (
              <div className="company-profile__list company-profile__list--cannot">
                <h4>{t('profileCannotShow')}</h4>
                <ul>
                  {company.cannot_show.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
