import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import { MenuIcon } from './components/icons'
import CareerAdvisor from './pages/CareerAdvisor'
import MarketInsights from './pages/MarketInsights'
import AIResults from './pages/AIResults'
import { fetchMarketInsights, submitCareerAnalysis } from './services/api'
import './App.css'

function parseSkills(rawSkills) {
  return rawSkills
    .split(',')
    .map((skill) => skill.trim())
    .filter(Boolean)
}

function App() {
  const [activePage, setActivePage] = useState('advisor')
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const [targetRole, setTargetRole] = useState('Data Engineer')
  const [currentSkills, setCurrentSkills] = useState('Java, Spring Boot, SQL, REST API')

  const [insights, setInsights] = useState({ status: 'loading', data: null, error: '', demo: false })
  const [analysis, setAnalysis] = useState({ status: 'idle', data: null, error: '', demo: false })

  useEffect(() => {
    let cancelled = false

    fetchMarketInsights()
      .then((data) => {
        if (cancelled) return
        setInsights({ status: 'success', data, error: '', demo: Boolean(data.demo) })
      })
      .catch((error) => {
        if (cancelled) return
        setInsights({ status: 'error', data: null, error: error.message, demo: false })
      })

    return () => {
      cancelled = true
    }
  }, [])

  const handleNavigate = (pageId) => {
    setActivePage(pageId)
    setIsSidebarOpen(false)
  }

  const handleAnalyze = async () => {
    const skills = parseSkills(currentSkills)

    if (!targetRole || skills.length === 0) {
      setAnalysis({ status: 'error', data: null, error: 'Please provide a target role and at least one skill.', demo: false })
      return
    }

    setAnalysis({ status: 'loading', data: null, error: '', demo: false })

    try {
      const data = await submitCareerAnalysis({ targetRole, currentSkills: skills })
      setAnalysis({ status: 'success', data, error: '', demo: Boolean(data.demo) })
      setActivePage('results')
    } catch (error) {
      setAnalysis({ status: 'error', data: null, error: error.message, demo: false })
    }
  }

  const currentDemo = activePage === 'insights' ? insights.demo : activePage === 'results' ? analysis.demo : insights.demo || analysis.demo

  return (
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        onNavigate={handleNavigate}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        isDemo={currentDemo}
      />

      <div className="app-main">
        <header className="mobile-topbar">
          <button className="icon-btn" onClick={() => setIsSidebarOpen(true)} aria-label="Open navigation">
            <MenuIcon />
          </button>
          <span className="brand-name">AI Career Navigator</span>
        </header>

        <main className="main-content">
          {activePage === 'advisor' && (
            <CareerAdvisor
              targetRole={targetRole}
              setTargetRole={setTargetRole}
              currentSkills={currentSkills}
              setCurrentSkills={setCurrentSkills}
              onAnalyze={handleAnalyze}
              status={analysis.status}
              errorMessage={analysis.error}
            />
          )}

          {activePage === 'insights' && (
            <MarketInsights
              data={insights.data}
              status={insights.status}
              errorMessage={insights.error}
              isDemo={insights.demo}
            />
          )}

          {activePage === 'results' && (
            <AIResults
              targetRole={targetRole}
              results={analysis.data}
              status={analysis.status}
              errorMessage={analysis.error}
              isDemo={analysis.demo}
            />
          )}
        </main>
      </div>
    </div>
  )
}

export default App
