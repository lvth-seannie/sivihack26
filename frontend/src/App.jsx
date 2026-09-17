import { useCallback, useEffect, useState } from 'react'
import logo from './assets/OmniNode_logo.png'
import { fetchCompanies, fetchResults, screenCompany } from './api'
import ResultsBoard from './components/ResultsBoard'
import CompanySummary from './components/CompanySummary'
import EmptyState from './components/EmptyState'
import { formatDateTime } from './lib/format'
import './App.css'

function App() {
  const [companies, setCompanies] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    fetchCompanies()
      .then((list) => {
        setCompanies(list)
        if (list.length > 0) setSelectedId(list[0].id)
      })
      .catch(() => setError('Không thể tải danh sách công ty. Kiểm tra kết nối backend.'))
  }, [])

  useEffect(() => {
    if (selectedId == null) return undefined
    let cancelled = false
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
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const handleScreen = useCallback(async () => {
    if (selectedId == null) return
    setLoading(true)
    setError(null)
    try {
      const data = await screenCompany(selectedId)
      setResult(data)
      setFlash(true)
      setTimeout(() => setFlash(false), 1200)
    } catch {
      setError('Sàng lọc thất bại. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  const selectedCompany = companies.find((c) => c.id === selectedId)

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <img src={logo} alt="OmniNode" className="app-header__logo" />
          <div>
            <h1>Tender AI Screening</h1>
            <p>Sàng lọc gói thầu theo luật tất định — không dùng LLM</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="control-bar">
          <label className="control-bar__field">
            <span>Công ty</span>
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

          <button className="btn-primary" onClick={handleScreen} disabled={loading || selectedId == null}>
            {loading ? 'Đang sàng lọc…' : 'Screen tenders'}
          </button>

          {result?.summary && (
            <div className={`summary-chips${flash ? ' is-flash' : ''}`}>
              <span className="chip chip--candidate">{result.summary.CANDIDATE} candidates</span>
              <span className="chip chip--flag">{result.summary.FLAG} flags</span>
              <span className="chip chip--hardfail">{result.summary.HARD_FAIL} hard fails</span>
            </div>
          )}

          {result?.generated_at && (
            <span className="control-bar__status">Cập nhật lúc {formatDateTime(result.generated_at)}</span>
          )}
        </div>

        {selectedCompany && <CompanySummary company={selectedCompany} />}

        {error && <p className="app-error">{error}</p>}

        {!result && !error && <p className="app-loading">Đang tải…</p>}

        {result &&
          (result.screened ? (
            <div className={`results-board-wrap${flash ? ' is-flash' : ''}`} key={selectedId}>
              <ResultsBoard tenders={result.tenders} />
            </div>
          ) : (
            <EmptyState onScreen={handleScreen} loading={loading} />
          ))}
      </main>
    </div>
  )
}

export default App
