import { formatCurrency, formatKm } from '../lib/format'

const L = 'vi'

export default {
  ui: {
    appTitle: 'Sàng lọc gói thầu AI',
    appSubtitle: 'Công cụ luật tất định — không dùng LLM để ra quyết định',
    heroSubtitle: 'Chọn hồ sơ công ty, sau đó sàng lọc trên toàn bộ gói thầu đang mở.',
    companyLabel: 'Công ty',
    screenButton: 'Sàng lọc gói thầu',
    screeningButton: 'Đang sàng lọc…',
    loadingCompanies: 'Đang tải danh sách công ty…',
    loading: 'Đang tải…',
    companyLoadError: 'Không thể tải danh sách công ty. Kiểm tra kết nối backend.',
    companyLoadErrorTitle: 'Sự cố kết nối',
    screenError: 'Sàng lọc thất bại. Vui lòng thử lại.',
    retry: 'Thử lại',
    loadingResultsLabel: 'Đang tải kết quả…',
    updatedAt: 'Cập nhật lúc {time}',
    chipCandidates: '{n} ứng viên',
    chipFlags: '{n} cảnh báo',
    chipHardFails: '{n} loại trừ',
    emptyStateText: 'Chưa có kết quả sàng lọc cho công ty này.',
    sectionCandidatesTitle: 'Ứng viên',
    sectionCandidatesDesc: 'Đáp ứng đủ điều kiện — nên đấu thầu',
    sectionFlagsTitle: 'Cảnh báo',
    sectionFlagsDesc: 'Đạt điều kiện nhưng cần lưu ý',
    sectionHardFailsTitle: 'Loại trừ',
    sectionHardFailsDesc: 'Không đạt điều kiện knockout',
    sectionEmpty: 'Không có mục nào trong mục này.',
    viewSource: 'Xem chi tiết nguồn',
    hideSource: 'Ẩn chi tiết nguồn',
    sourceLink: 'Nguồn ↗',
    pageLabel: 'Trang {n}',
    lotDiffersWarning: 'Khác với kết quả của gói thầu chính — đừng bỏ lỡ',
    lotLabel: 'Lot {n}',
    lotOfTender: 'Lot {n} thuộc gói thầu',
    tenderParentVerdict: 'Kết quả gói thầu chính',
    profileTitle: 'Hồ sơ công ty',
    profileToggleShow: 'Xem hồ sơ công ty',
    profileToggleHide: 'Ẩn hồ sơ công ty',
    profileFounded: 'Thành lập',
    profileEmployees: 'Nhân viên',
    profileRevenue: 'Doanh thu',
    profileHq: 'Trụ sở',
    profileRadius: 'Bán kính hoạt động',
    profileContractRange: 'Quy mô hợp đồng',
    profileGuaranteeCeiling: 'Hạn mức bảo lãnh',
    profileAvailableFrom: 'Sẵn sàng từ',
    profileCanShow: 'Kinh nghiệm đã chứng minh',
    profileCannotShow: 'Không thể đảm nhận',
    languageLabel: 'Ngôn ngữ',
    verdictCandidate: 'Ứng viên',
    verdictFlag: 'Cảnh báo',
    verdictHardFail: 'Loại trừ',
  },
  reasons: {
    OUT_OF_RADIUS: (ctx) =>
      `Khoảng cách ${formatKm(ctx.distance_km, L)} vượt bán kính hoạt động ${formatKm(ctx.radius_km, L)}.`,
    OUT_OF_VALUE_RANGE: (ctx) =>
      `Giá trị ${formatCurrency(ctx.value, L)} nằm ngoài khoảng ${formatCurrency(ctx.min, L)}–${formatCurrency(ctx.max, L)} mà công ty này nhận thầu.`,
    GUARANTEE_OVER_CEILING: (ctx) =>
      `Bảo lãnh yêu cầu ${formatCurrency(ctx.guarantee_required, L)} vượt hạn mức ${formatCurrency(ctx.ceiling, L)}.`,
    MISSING_REFERENCES: (ctx) =>
      `Thiếu tham chiếu bắt buộc: ${ctx.missing.join(', ')}.`,
    CAPABILITY_EXCLUDED: (ctx) =>
      `Yêu cầu thuộc năng lực đã loại trừ: ${ctx.excluded.join(', ')}.`,
    GUARANTEE_NEAR_CEILING: (ctx) =>
      `Bảo lãnh yêu cầu ${formatCurrency(ctx.guarantee_required, L)} đạt ${ctx.ratio_pct}% hạn mức ${formatCurrency(ctx.ceiling, L)}.`,
    CANDIDATE_OK: () =>
      'Đáp ứng bán kính hoạt động, giá trị hợp đồng, hạn mức bảo lãnh và tham chiếu yêu cầu.',
  },
}
