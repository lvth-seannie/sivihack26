import { useLanguage } from '../i18n/useLanguage'

const LABEL_KEYS = {
  CANDIDATE: 'verdictCandidate',
  FLAG: 'verdictFlag',
  HARD_FAIL: 'verdictHardFail',
}

export default function VerdictBadge({ verdict, small = false }) {
  const { t } = useLanguage()
  const modifier = verdict.toLowerCase().replace('_', '-')
  return (
    <span className={`verdict-badge verdict-badge--${modifier}${small ? ' verdict-badge--sm' : ''}`}>
      {t(LABEL_KEYS[verdict] ?? verdict)}
    </span>
  )
}
