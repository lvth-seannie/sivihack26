import { TrendUpIcon, TrendDownIcon } from '../components/icons'

function MeterRow({ name, percentage }) {
  return (
    <div className="meter-row">
      <div className="meter-row-head">
        <span>{name}</span>
        <strong>{percentage}%</strong>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${Math.min(100, percentage)}%` }} />
      </div>
    </div>
  )
}

function MeterCard({ title, items }) {
  return (
    <div className="card">
      <label className="label">{title}</label>
      {items.map((item) => (
        <MeterRow key={item.name} name={item.name} percentage={item.percentage} />
      ))}
    </div>
  )
}

function MarketInsights({ data, status, errorMessage, isDemo }) {
  if (status === 'loading') {
    return (
      <div className="page">
        <header className="page-header">
          <p className="page-eyebrow">Step 2</p>
          <h1 className="page-title">Market Insights</h1>
        </header>
        <div className="card state-card">Loading aggregated market data…</div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="page">
        <header className="page-header">
          <p className="page-eyebrow">Step 2</p>
          <h1 className="page-title">Market Insights</h1>
        </header>
        <div className="alert alert--error">
          {errorMessage || 'Could not load market insights from the backend.'}
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-header">
        <p className="page-eyebrow">Step 2</p>
        <h1 className="page-title">Market Insights</h1>
        <p className="page-subtitle">
          Aggregated live from the jobs, skills, companies and roles tables in PostgreSQL.
          {isDemo && ' Currently showing demo data — connect VITE_MARKET_INSIGHTS_URL to go live.'}
        </p>
      </header>

      <div className="grid-responsive">
        <MeterCard title="Top Required Skills" items={data.topSkills} />
        <MeterCard title="Top Roles" items={data.topRoles} />
        <MeterCard title="Top Hiring Locations" items={data.topLocations} />

        <div className="card">
          <label className="label">Market Trends</label>
          {data.trends.map((trend) => (
            <div className="trend-row" key={trend.label}>
              <span>{trend.label}</span>
              <span className={`trend-value ${trend.direction === 'up' ? 'is-up' : 'is-down'}`}>
                {trend.direction === 'up' ? <TrendUpIcon /> : <TrendDownIcon />}
                {trend.percentage}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default MarketInsights
