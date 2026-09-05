import { CompassIcon, ChartIcon, SparkleIcon, CloseIcon } from './icons'

const NAV_ITEMS = [
  { id: 'advisor', label: 'Career Advisor', step: '1', icon: CompassIcon },
  { id: 'insights', label: 'Market Insights', step: '2', icon: ChartIcon },
  { id: 'results', label: 'AI Results', step: '3', icon: SparkleIcon },
]

function Sidebar({ activePage, onNavigate, isOpen, onClose, isDemo }) {
  return (
    <>
      <div className={`sidebar-scrim ${isOpen ? 'is-visible' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? 'is-open' : ''}`}>
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-mark">AI</span>
            <span className="brand-name">Career Navigator</span>
          </div>
          <button className="sidebar-close" onClick={onClose} aria-label="Close navigation">
            <CloseIcon />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ id, label, step, icon: Icon }) => (
            <button
              key={id}
              className={`sidebar-link ${activePage === id ? 'is-active' : ''}`}
              onClick={() => onNavigate(id)}
            >
              <span className="sidebar-link-icon">
                <Icon />
              </span>
              <span className="sidebar-link-text">
                <span className="sidebar-link-step">Step {step}</span>
                <span>{label}</span>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className={`status-chip ${isDemo ? 'is-demo' : 'is-live'}`}>
            <span className="status-dot" />
            {isDemo ? 'demo data' : 'Live backend'}
          </div>
          <p className="sidebar-footer-note">
            Job Dataset &rarr; PostgreSQL &rarr; n8n &rarr; OpenAI/Claude
          </p>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
