export default function EmptyState({ onScreen, loading }) {
  return (
    <div className="empty-state">
      <p>Chưa có kết quả sàng lọc cho công ty này.</p>
      <button className="btn-primary" onClick={onScreen} disabled={loading}>
        {loading ? 'Đang sàng lọc…' : 'Screen tenders'}
      </button>
    </div>
  )
}
