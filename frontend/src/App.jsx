import { useCallback, useEffect, useMemo, useState } from 'react'
import logo from './assets/OmniNode_logo.png'
import { fetchCompanies, fetchResults, screenCompany } from './api'
import ResultsBoard from './components/ResultsBoard'
import ResultsSkeleton from './components/ResultsSkeleton'
import CompanyProfile from './components/CompanyProfile'
import EmptyState from './components/EmptyState'
import ErrorAlert from './components/ErrorAlert'
import LanguageSwitcher from './components/LanguageSwitcher'
import { LanguageProvider } from './i18n/LanguageContext'
import { useLanguage } from './i18n/useLanguage'
import { formatDateTime } from './lib/format'
import { countSections } from './lib/grouping'
import './App.css'

function AppContent() {
  const { locale, t } = useLanguage()
  const [companies, setCompanies] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [result, setResult] = useState(null)
  const [screening, setScreening] = useState(false)
  const [fetchingResults, setFetchingResults] = useState(false)
  const [error, setError] = useState(null) // 'companies' | 'screen' | null
  const [flash, setFlash] = useState(false)

  const loadCompanies = useCallback(() => {
    fetchCompanies()
      .then((list) => {
        setCompanies(list)
        setError(null)
        if (list.length > 0) setSelectedId((prev) => prev ?? list[0].id)
      })
      .catch(() => setError('companies'))
  }, [])

  useEffect(() => {
    loadCompanies()
  }, [loadCompanies])

  useEffect(() => {
    if (selectedId == null) return undefined
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag must flip true before the fetch settles
    setFetchingResults(true)
    fetchResults(selectedId)
      .then((data) => {
        if (!cancelled) {
          setResult(data)
          setError(null)
        }
      })
      .catch(() => {
        if (!cancelled) setResult(null)
      })
      .finally(() => {
        if (!cancelled) setFetchingResults(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const handleScreen = useCallback(async () => {
    if (selectedId == null) return
    setScreening(true)
    setError(null)
    try {
      const data = await screenCompany(selectedId)
      setResult(data)
      setFlash(true)
      setTimeout(() => setFlash(false), 1200)
    } catch {
      setError('screen')
    } finally {
      setScreening(false)
    }
  }, [selectedId])

  const selectedCompany = companies.find((c) => c.id === selectedId)
  const busy = screening || fetchingResults
  // Same buildSections() the section headers below use, so the pills can
  // never drift out of sync with them - see lib/grouping.js.
  const summary = useMemo(() => (result?.tenders ? countSections(result.tenders) : null), [result])

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <div className="app-header__brand">
            <img src={logo} alt="OmniNode" className="app-header__logo" />
            <span className="app-header__wordmark">{t('appTitle')}</span>
          </div>
          <LanguageSwitcher />
        </div>
      </header>

      <section className="hero">
        <div className="hero__card">
          <p className="hero__eyebrow">{t('appSubtitle')}</p>
          <h1 className="hero__title">{t('appTitle')}</h1>
          <p className="hero__subtitle">{t('heroSubtitle')}</p>

          <div className="hero__controls">
            <label className="hero__field">
              <span>{t('companyLabel')}</span>
              <select
                value={selectedId ?? ''}
                onChange={(e) => setSelectedId(Number(e.target.value))}
                disabled={companies.length === 0}
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>

            <button
              className="btn-primary btn-primary--lg"
              onClick={handleScreen}
              disabled={screening || selectedId == null}
            >
              {screening ? t('screeningButton') : t('screenButton')}
            </button>
          </div>

          {summary && (
            <div className={`summary-chips${flash ? ' is-flash' : ''}`}>
              <span className="chip chip--candidate">{t('chipCandidates', { n: summary.CANDIDATE })}</span>
              <span className="chip chip--flag">{t('chipFlags', { n: summary.FLAG })}</span>
              <span className="chip chip--hardfail">{t('chipHardFails', { n: summary.HARD_FAIL })}</span>
            </div>
          )}

          {result?.generated_at && (
            <span className="hero__status">{t('updatedAt', { time: formatDateTime(result.generated_at, locale) })}</span>
          )}

          {error && (
            <ErrorAlert
              title={t('companyLoadErrorTitle')}
              message={t(error === 'companies' ? 'companyLoadError' : 'screenError')}
              onRetry={error === 'companies' ? loadCompanies : handleScreen}
            />
          )}
        </div>
      </section>

      <main className="app-main">
        {selectedCompany && <CompanyProfile company={selectedCompany} />}

        {busy ? (
          <ResultsSkeleton />
        ) : (
          result &&
          (result.screened ? (
            <div className={`results-board-wrap${flash ? ' is-flash' : ''}`} key={selectedId}>
              <ResultsBoard tenders={result.tenders} />
            </div>
          ) : (
            <EmptyState onScreen={handleScreen} loading={screening} />
          ))
        )}
      </main>
    </div>
  )
}

function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  )
}

export default App
