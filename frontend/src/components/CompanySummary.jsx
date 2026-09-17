import { formatCurrency } from '../lib/format'

export default function CompanySummary({ company }) {
  return (
    <div className="company-summary">
      <span>
        <strong>Bán kính hoạt động</strong> {company.region_radius_km} km từ {company.region_center}
      </span>
      <span>
        <strong>Giá trị hợp đồng</strong> {formatCurrency(company.contract_min)} – {formatCurrency(company.contract_max)}
      </span>
      <span>
        <strong>Hạn mức bảo lãnh</strong> {formatCurrency(company.guarantee_ceiling)}
      </span>
    </div>
  )
}
