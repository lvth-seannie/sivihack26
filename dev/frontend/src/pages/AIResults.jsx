import { CheckIcon, CrossIcon, SparkleIcon } from '../components/icons'

function AIResults({ targetRole, results, status, errorMessage, isDemo }) {
  if (status === 'idle') {
    return (
      <div className="page">
        <header className="page-header">
          <p className="page-eyebrow">Step 3</p>
          <h1 className="page-title">AI Results</h1>
        </header>
        <div className="card state-card">
          Run an analysis from the Career Advisor page to see your results here.
        </div>
      </div>
    )
  }

  if (status === 'loading') {
    return (
      <div className="page">
        <header className="page-header">
          <p className="page-eyebrow">Step 3</p>
          <h1 className="page-title">AI Results</h1>
        </header>
        <div className="card state-card">Calculating skill gap and building your roadmap…</div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="page">
        <header className="page-header">
          <p className="page-eyebrow">Step 3</p>
          <h1 className="page-title">AI Results</h1>
        </header>
        <div className="alert alert--error">{errorMessage || 'The analysis could not be completed.'}</div>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-header">
        <p className="page-eyebrow">Step 3</p>
        <h1 className="page-title">AI Results</h1>
        <p className="page-subtitle">
          Structured output from the AI pipeline for <strong>{targetRole}</strong>.
          {isDemo && ' Currently showing demo output — connect VITE_N8N_WEBHOOK_URL to go live.'}
        </p>
      </header>

      <div className="grid-responsive">
        <div className="card card--score">
          <label className="label">Market Fit Score</label>
          <div className="score-circle">{results.matchScore}%</div>
          <p className="score-caption">
            Target role: <strong>{targetRole}</strong>
          </p>
        </div>

        <div className="card">
          <label className="label">Strengths</label>
          <div className="pill-row">
            {results.strengths.length ? (
              results.strengths.map((skill) => (
                <span className="pill pill--success" key={skill}>
                  <CheckIcon /> {skill}
                </span>
              ))
            ) : (
              <p className="empty-note">No overlapping strengths found yet — every required skill is a growth area.</p>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <label className="label">Skill Gap Comparison</label>
        <div className="gap-comparison">
          <div>
            <span className="gap-comparison-title">You have</span>
            {results.strengths.map((skill) => (
              <div className="list-item" key={skill}>
                <span>{skill}</span>
                <span className="status-good">
                  <CheckIcon /> Active
                </span>
              </div>
            ))}
            {!results.strengths.length && <p className="empty-note">Nothing yet.</p>}
          </div>
          <div>
            <span className="gap-comparison-title">Still need</span>
            {results.missingSkills.map((skill) => (
              <div className="list-item" key={skill}>
                <span>{skill}</span>
                <span className="status-bad">
                  <CrossIcon /> Missing
                </span>
              </div>
            ))}
            {!results.missingSkills.length && <p className="empty-note">You're fully covered.</p>}
          </div>
        </div>
      </div>

      <div className="card">
        <label className="label">Generated Learning Roadmap</label>
        <div className="grid-responsive grid-responsive--tight">
          {results.roadmap.map((step) => (
            <div className="roadmap-step" key={step.phase + step.skill}>
              <span className="roadmap-phase">{step.phase}</span>
              <h3>{step.skill}</h3>
              {step.description && <p>{step.description}</p>}
            </div>
          ))}
          {!results.roadmap.length && <p className="empty-note">No further learning steps required.</p>}
        </div>
      </div>

      {results.recommendation && (
        <div className="card card--recommendation">
          <label className="label">
            <SparkleIcon /> AI Recommendation
          </label>
          <p>{results.recommendation}</p>
        </div>
      )}
    </div>
  )
}

export default AIResults
