import { useMemo, useState } from 'react'
import { LanguageContext } from './context'
import { DICTIONARIES } from './dictionaries'

const STORAGE_KEY = 'tender-screening-lang'

function interpolate(str, params) {
  if (!params) return str
  return str.replace(/\{(\w+)\}/g, (_, key) => (params[key] ?? `{${key}}`))
}

function readStoredLocale() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved && DICTIONARIES[saved] ? saved : null
  } catch {
    return null
  }
}

export function LanguageProvider({ children }) {
  const [locale, setLocaleState] = useState(() => readStoredLocale() ?? 'en')

  const setLocale = (next) => {
    if (!DICTIONARIES[next]) return
    setLocaleState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // per-viewer convenience only - fine if storage is unavailable
    }
  }

  const value = useMemo(() => {
    const dict = DICTIONARIES[locale]
    return {
      locale,
      setLocale,
      t: (key, params) => interpolate(dict.ui[key] ?? key, params),
      reasonText: (reasonCode, context) => {
        const fn = dict.reasons[reasonCode]
        const base = fn ? fn(context ?? {}) : reasonCode
        const citation = context?.citation
        if (!citation?.snippet) return base
        const key = citation.page != null ? 'citationWithPage' : 'citationNoPage'
        return `${base} ${interpolate(dict.ui[key], citation)}`
      },
    }
  }, [locale])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
