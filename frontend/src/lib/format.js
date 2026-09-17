const LOCALE_TAGS = { en: 'en-US', de: 'de-DE', vi: 'vi-VN' }

function tag(locale) {
  return LOCALE_TAGS[locale] ?? 'en-US'
}

export function formatCurrency(value, locale = 'en') {
  if (value == null) return '—'
  return new Intl.NumberFormat(tag(locale), {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatNumber(value, locale = 'en') {
  if (value == null) return '—'
  return new Intl.NumberFormat(tag(locale)).format(value)
}

export function formatKm(value, locale = 'en') {
  if (value == null) return '—'
  return `${new Intl.NumberFormat(tag(locale), { maximumFractionDigits: 1 }).format(Number(value))} km`
}

export function formatDateTime(value, locale = 'en') {
  if (!value) return null
  return new Intl.DateTimeFormat(tag(locale), { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  )
}

export function formatDate(value, locale = 'en') {
  if (!value) return null
  return new Intl.DateTimeFormat(tag(locale), { dateStyle: 'long' }).format(new Date(value))
}
