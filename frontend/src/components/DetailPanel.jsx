export default function DetailPanel({ sourceSnippet, sourcePage, sourceUrl }) {
  if (!sourceSnippet && sourcePage == null && !sourceUrl) return null

  return (
    <div className="detail-panel">
      {sourceSnippet && <p className="detail-panel__snippet">&ldquo;{sourceSnippet}&rdquo;</p>}
      <div className="detail-panel__meta">
        {sourcePage != null && <span>Trang {sourcePage}</span>}
        {sourceUrl && (
          <a href={sourceUrl} target="_blank" rel="noreferrer">
            Nguồn gói thầu ↗
          </a>
        )}
      </div>
    </div>
  )
}
