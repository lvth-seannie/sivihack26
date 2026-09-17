const LABELS = {
  CANDIDATE: 'Candidate',
  FLAG: 'Flag',
  HARD_FAIL: 'Hard fail',
}

export default function VerdictBadge({ verdict, small = false }) {
  const modifier = verdict.toLowerCase().replace('_', '-')
  return (
    <span className={`verdict-badge verdict-badge--${modifier}${small ? ' verdict-badge--sm' : ''}`}>
      {LABELS[verdict] ?? verdict}
    </span>
  )
}
