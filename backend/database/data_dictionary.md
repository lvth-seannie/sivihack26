# Data Dictionary — "Three Out of Forty" (SiviHack 2026)

Tài liệu mô tả chi tiết schema PostgreSQL tại `backend/database/schema.sql`, dữ liệu mẫu tại
`backend/database/seed_companies.sql`, và nguồn dữ liệu tại `backend/database/raw_data/`.

## Mục lục
- [Tổng quan mô hình](#tổng-quan-mô-hình)
- [ENUM: verdict_type](#enum-verdict_type)
- [buyers](#buyers)
- [companies](#companies)
- [cpv_codes](#cpv_codes)
- [tenders](#tenders)
- [lots](#lots)
- [lot_requirements](#lot_requirements)
- [lot_award_results](#lot_award_results)
- [verdicts](#verdicts)
- [Function: great_circle_km](#function-great_circle_km)
- [Views](#views)
- [Nguồn dữ liệu chưa map / hạn chế đã biết](#nguồn-dữ-liệu-chưa-map--hạn-chế-đã-biết)

---

## Tổng quan mô hình

```
buyers ──< tenders ──< lots ──< lot_requirements
                          │  \
                          │   └──1:1── lot_award_results
                          │
              companies ──< verdicts >── (lots, tenders, lot_requirements)
```

- **1 tender luôn có ≥ 1 lot.** Kể cả gói không chia lot vẫn có đúng 1 lot ảo (`lot_identifier = 'LOT-0000'`),
  phản ánh đúng cấu trúc dữ liệu nguồn eForms/TED — nhờ vậy `verdicts.lot_id` luôn `NOT NULL`, không cần xử lý
  trường hợp "verdict cấp gói vs verdict cấp lot" mập mờ bằng NULL.
- **`verdicts` là bảng append-only** — mỗi lần engine chạy lại sẽ `INSERT` dòng mới thay vì `UPDATE`, giữ lịch sử
  audit khi dữ liệu công ty/gói thầu thay đổi. Dùng view `latest_verdicts` để lấy kết quả mới nhất.
  `tender_verdict_summary` gộp verdict xấu nhất trong các lot con thành verdict đại diện cấp gói.
  Thứ tự "xấu nhất": `HARD_FAIL` > `FLAG` > `CANDIDATE`.
- **Vùng hoạt động dùng mô hình tâm-điểm + bán kính** (`region_center` + `region_radius_km` trên `companies`,
  `place_lat`/`place_lon` trên `lots`), so khớp bằng khoảng cách đường chim bay qua hàm `great_circle_km()` —
  chính xác hơn so khớp theo mã NUTS/tên vùng hành chính.
- **Năng lực dùng chung 1 bộ "tag" tự do** giữa `companies.references_held` / `companies.capabilities_excluded`
  và `lots.required_capabilities` (vd `'road_construction'`, `'high_voltage'`) — không dùng mã CPV để ra quyết
  định vì CPV chỉ mang tính phân loại hành chính, quá thô để tạo ra khác biệt rõ rệt giữa các công ty.
- Các cột không thể lấy trực tiếp từ dữ liệu có cấu trúc (CSV/API) — số tiền bảo lãnh cụ thể, số lượng dự án
  tham chiếu yêu cầu, chứng chỉ... — được AI trích xuất từ tài liệu PDF gốc và lưu vào `lot_requirements`, kèm
  trích đoạn nguồn (`source_excerpt`) + số trang (`source_page`) làm bằng chứng.

---

## ENUM: verdict_type

| Giá trị | Ý nghĩa |
|---|---|
| `HARD_FAIL` | Loại thẳng do vi phạm ràng buộc cứng (vd ngoài bán kính hoạt động, thiếu năng lực bắt buộc, gói đã có người trúng thầu). |
| `FLAG` | Rủi ro nhưng còn tranh luận được — cần review thủ công (vd thiếu dữ liệu để kết luận chắc chắn, gần biên giá trị/bán kính). |
| `CANDIDATE` | Đạt tất cả ràng buộc cứng đã kiểm tra, có thể tham gia đấu thầu. |

---

## buyers

Bên mời thầu (chủ đầu tư/cơ quan công quyền), dedup theo `organisation_identifier` để tránh lặp dữ liệu vì
`organisation.csv` gốc lặp lại thông tin buyer ở mỗi notice.

| Cột | Kiểu | Bắt buộc | Nguồn CSV / Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `organisation_identifier` | TEXT (UNIQUE) | | `organisation.organisationIdentifier` — mã định danh pháp nhân (vd `"11-1393306000-19"`) |
| `name` | TEXT | ✔ | `organisation.organisationName` |
| `city` | TEXT | | `organisation.organisationCity` |
| `post_code` | TEXT | | `organisation.organisationPostCode` |
| `country_subdivision` | TEXT | | `organisation.organisationCountrySubdivision` — mã NUTS, vd `"DE300"` |
| `country_code` | TEXT | | `organisation.organisationCountryCode` — vd `"DEU"` |
| `website` | TEXT | | `organisation.organisationInternetAddress` |
| `legal_type` | TEXT | | `organisation.buyerLegalType` — vd `omu-lbeh`, `koerp-oer-kommun` |
| `is_contracting_entity` | BOOLEAN | | `organisation.buyerContractingEntity` — `true` = ngành tiện ích/hạ tầng theo Directive 2014/25, `false`/NULL = cơ quan công quyền thường |
| `created_at` | TIMESTAMPTZ | ✔ | `now()` |

---

## companies

Hồ sơ công ty mẫu tham gia sàng lọc. **Cấu trúc theo đúng Appendix A của đề bài**, không phải khung NUTS-array
ban đầu — xem seed thực tế tại `seed_companies.sql`.

| Cột | Kiểu | Bắt buộc | Nguồn / Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `name` | TEXT | ✔ | Appendix A: `name` |
| `region_center` | TEXT | ✔ | Appendix A: `region_center` — tên thành phố trung tâm vùng hoạt động (vd `'Augsburg'`) |
| `region_center_lat` | NUMERIC(9,6) | | **Không có trong Appendix A** — cần geocode riêng (vd Nominatim/OSM) trước khi dùng `great_circle_km()` |
| `region_center_lon` | NUMERIC(9,6) | | như trên |
| `region_radius_km` | INTEGER | ✔ (>0) | Appendix A: `region_radius_km` — bán kính công ty sẵn sàng di chuyển tới công trường |
| `contract_min` | NUMERIC(18,2) | | Appendix A: `contract_min` |
| `contract_max` | NUMERIC(18,2) | | Appendix A: `contract_max` — CHECK `contract_min <= contract_max` khi cả hai có giá trị |
| `contract_currency` | TEXT | ✔ | Mặc định `'EUR'`, không có trong INSERT mẫu |
| `guarantee_ceiling` | NUMERIC(18,2) | | Appendix A: `guarantee_ceiling` — **có thể NULL** khi công ty không khai trần cụ thể (vd Hanseatische Bau AG). Engine phải coi NULL là "chưa biết", không phải "không giới hạn" |
| `guarantee_currency` | TEXT | ✔ | Mặc định `'EUR'` |
| `references_held` | TEXT[] | ✔ (mặc định `{}`) | Appendix A: `references_held` — tag kinh nghiệm/năng lực đã có (vd `'road_construction'`, `'sewer_pipeline'`), cùng vocabulary với `lots.required_capabilities` |
| `capabilities_excluded` | TEXT[] | ✔ (mặc định `{}`) | Appendix A: `capabilities_excluded` — tag năng lực KHÔNG có; nguồn chính tạo `HARD_FAIL` đặc thù theo từng công ty |
| `available_from` | DATE | | Appendix A: `available_from` — công ty chỉ nhận việc từ ngày này (NULL = sẵn sàng ngay); so với `lots.duration_start_date` |
| `weekly_bid_capacity` | INTEGER | (>0 nếu có) | **Không có trong Appendix A gốc** — thêm theo gợi ý của đề bài cho Hanseatische Bau AG (ràng buộc thật là năng lực đấu thầu ~3 tender/tuần, không phải bảo lãnh) |
| `created_at` / `updated_at` | TIMESTAMPTZ | ✔ | `now()` |

**Index:** GIN trên `references_held`, `capabilities_excluded` (phục vụ `&&`, `@>`, `<@`).

---

## cpv_codes

Từ điển mã CPV (Common Procurement Vocabulary) — bảng tra cứu tuỳ chọn, **không bắt buộc cho MVP**. Không đặt
FK cứng từ `tenders`/`lots` tới bảng này vì dữ liệu CPV thật luôn có mã chưa kịp nạp vào từ điển.

| Cột | Kiểu | Nguồn / Ghi chú |
|---|---|---|
| `code` | TEXT (PK) | Mã CPV 8 chữ số, vd `'45262100'` |
| `description_en` | TEXT | Cần nạp từ danh mục CPV chính thức EU (không có trong `raw_data`) hoặc trích từ cột `"Main classification"` (dạng text) trong `TED_17-09-2026.csv` |
| `description_de` | TEXT | như trên |

---

## tenders

Gói thầu ở cấp toàn bộ thủ tục mời thầu (1 dòng = 1 *notice*). **Lưu ý quan trọng:** file gốc `tender.csv`
trong `raw_data/` **không phải** dữ liệu cho bảng này — đó là hồ sơ dự thầu đã nộp (kết quả sau đấu thầu), được
map vào `lot_award_results`. Khái niệm "gói thầu" ở đây gộp từ `notice.csv + procedure.csv + purpose.csv`
(dòng không có `lotIdentifier`) `+ classification.csv` (dòng không có `lotIdentifier`).

| Cột | Kiểu | Bắt buộc | Nguồn CSV / Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `notice_identifier` | UUID | ✔ | `notice.noticeIdentifier` — cùng `notice_version` tạo khoá tự nhiên `UNIQUE`, dùng cho ETL `ON CONFLICT` |
| `notice_version` | TEXT | ✔ | `notice.noticeVersion` |
| `procedure_identifier` | UUID | | `notice.procedureIdentifier` |
| `buyer_id` | UUID (FK → buyers, `ON DELETE SET NULL`) | | |
| `title` | TEXT | | `purpose.title` (dòng `lotIdentifier IS NULL`) |
| `description` | TEXT | | `purpose.description` (dòng `lotIdentifier IS NULL`) |
| `main_nature` | TEXT (CHECK: `works`/`services`/`supplies`/NULL) | | `purpose.mainNature` |
| `main_cpv_code` | TEXT | | `classification.mainClassificationCode` (dòng `lotIdentifier IS NULL`) — không FK cứng tới `cpv_codes` |
| `main_cpv_description` | TEXT | | Fallback: text `"Main classification"` từ `TED_*.csv` khi chưa có trong `cpv_codes` |
| `estimated_value` | NUMERIC(18,2) | | `purpose.estimatedValue` (cấp gói, có thể NULL nếu chỉ khai theo từng lot) |
| `estimated_value_currency` | TEXT | | `purpose.estimatedValueCurrency`, mặc định `'EUR'` |
| `legal_basis` | TEXT | | `notice.procedureLegalBasis` — vd `'32014L0024'`, `'de-uvgo'` |
| `procedure_type` | TEXT | | `procedure.procedureType` — vd `'open'`, `'de-open'`, `'neg-w-call'`... Không `CHECK` vì danh mục eForms có thể mở rộng |
| `procedure_accelerated` | BOOLEAN | | `procedure.procedureAccelerated` |
| `cross_border_law` | TEXT | | `procedure.crossBorderLaw` |
| `lots_max_allowed` | INTEGER | | `procedure.lotsMaxAllowed` — số lot tối đa 1 nhà thầu được nộp hồ sơ |
| `lots_all_required` | BOOLEAN | | `procedure.lotsAllRequired` — bắt buộc dự thầu tất cả lot |
| `lots_max_awarded` | INTEGER | | `procedure.lotsMaxAwarded` |
| `notice_type` | TEXT | | `notice.noticeType` — vd `'cn-standard'`, `'can-standard'` |
| `form_type` | TEXT | | `notice.formType` — vd `'competition'`, `'result'`, `'change'` |
| `publication_date` | TIMESTAMPTZ | | `notice.publicationDate` |
| `notice_publication_number` | TEXT | | **Chỉ có trong `TED_*.csv`** ("Notice publication number", vd `'639077-2026'`) — KHÔNG có khoá UUID chung với các bảng eForms chi tiết, cần ETL đối chiếu tương đối (buyer + ngày đăng + CPV) |
| `submission_deadline` | TIMESTAMPTZ | | **Chỉ có trong `TED_*.csv`** ("Deadline for receipt of tenders") — cùng hạn chế join như trên |
| `source_document_url` | TEXT | | Link công khai tới tài liệu mời thầu gốc (PDF) trên nguồn thu thập — nguồn trích dẫn cho `verdicts` |
| `source_system` | TEXT (CHECK: `oeffentlichevergabe`/`ted`/`service_bund`/NULL) | | Nguồn thu thập gói thầu: `oeffentlichevergabe.de` là nguồn chính, TED là dự phòng cho gói lớn hơn ngưỡng EU, `service.bund.de` chỉ để đối chiếu |
| `raw_document_key` | TEXT | | Object key trong Backblaze B2 của PDF đã tải về — khác `source_document_url` (link công khai gốc); là khoá lưu trữ nội bộ dùng để AI trích xuất |
| `created_at` / `updated_at` | TIMESTAMPTZ | ✔ | `now()` |

**Index:** `buyer_id`, `main_cpv_code`, `publication_date`.

---

## lots

Từng phần (lot) của 1 gói thầu — **đơn vị chính để so sánh với hồ sơ công ty**. Mọi tender luôn có tối thiểu 1
lot (kể cả gói không chia lot có lot ảo `LOT-0000`).

| Cột | Kiểu | Bắt buộc | Nguồn CSV / Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `tender_id` | UUID (FK → tenders, `ON DELETE CASCADE`) | ✔ | |
| `lot_identifier` | TEXT | ✔ | `lot.lotIdentifier` — vd `'LOT-0000'`, `'LOT-0001'`. Cùng `tender_id` tạo `UNIQUE` |
| `internal_identifier` | TEXT | | `purpose.internalIdentifier` — mã nội bộ của bên mời thầu cho lot này |
| `title` | TEXT | | `purpose.title` (dòng có `lotIdentifier`) |
| `description` | TEXT | | `purpose.description` |
| `main_nature` | TEXT (CHECK: `works`/`services`/`supplies`/NULL) | | `purpose.mainNature` |
| `estimated_value` | NUMERIC(18,2) | | `purpose.estimatedValue` — giá trị dự kiến RIÊNG của lot, so khớp với `companies.contract_min/contract_max` |
| `estimated_value_currency` | TEXT | | `purpose.estimatedValueCurrency`, mặc định `'EUR'` |
| `main_cpv_code` | TEXT | | `classification.mainClassificationCode` (dòng có `lotIdentifier`) — giữ làm dữ liệu thô/tham khảo, không FK cứng tới `cpv_codes` |
| `additional_cpv_codes` | TEXT[] | ✔ (mặc định `{}`) | `classification.additionalClassificationCodes` (tách theo dấu phẩy) |
| `required_capabilities` | TEXT[] | ✔ (mặc định `{}`) | **Không có sẵn trong CSV/TED** — do AI trích xuất từ "Eignungskriterien"/"Referenzen" trong PDF (kết hợp suy luận từ CPV + mô tả lot). Cùng vocabulary tự do với `companies.references_held`/`capabilities_excluded`. Cột chính driving `HARD_FAIL`/`CANDIDATE` theo năng lực |
| `place_city` | TEXT | | `placeOfPerformance.placePerformanceCity` |
| `place_post_code` | TEXT | | `placeOfPerformance.placePerformancePostCode` |
| `place_country_subdivision` | TEXT | | `placeOfPerformance.placePerformanceCountrySubdivision` — mã NUTS, vd `'DE300'` |
| `place_country_code` | TEXT | | `placeOfPerformance.placePerformanceCountryCode` |
| `place_lat` / `place_lon` | NUMERIC(9,6) | | **Không có trong dữ liệu nguồn** — cần geocode riêng lúc ETL để dùng `great_circle_km()` với `companies.region_center_lat/lon` |
| `duration_start_date` / `duration_end_date` | DATE | | `duration.durationStartDate` / `durationEndDate` — Bauzeit/construction window, so với `companies.available_from` |
| `duration_period` | NUMERIC | | `duration.durationPeriod` (đi kèm `duration_period_unit`) |
| `duration_period_unit` | TEXT (CHECK: `DAY`/`WEEK`/`MONTH`/`YEAR`/NULL) | | `duration.durationPeriodUnit` |
| `renewal_maximum` | INTEGER | | `duration.renewalMaximum` — số lần gia hạn tối đa |
| `tender_validity_deadline_days` | NUMERIC | | `submissionTerms.tenderValidityDeadline` (đơn vị luôn `DAY` trong dữ liệu mẫu) |
| `guarantee_required` | BOOLEAN | | `submissionTerms.guaranteeRequired` — **chỉ là cờ true/false**, KHÔNG có số tiền; số tiền cụ thể (nếu trích xuất được) nằm ở `lot_requirements` |
| `public_opening_date` | TIMESTAMPTZ | | `submissionTerms.publicOpeningDate` |
| `suitable_for_smes` | BOOLEAN | | `additionalInformation.suitableForSMEs` |
| `strategic_procurement_flags` | TEXT | | `strategicProcurement.strategicProcurement` — vd `'none'`, `'env-imp,soc-obj'`. Thông tin ESG, không phải ràng buộc cứng nhưng có thể dùng cho `FLAG` |
| `created_at` / `updated_at` | TIMESTAMPTZ | ✔ | `now()` |

**Index:** `tender_id`, `main_cpv_code`, `place_country_subdivision`, `estimated_value`, `(place_lat, place_lon)`;
GIN trên `required_capabilities`, `additional_cpv_codes`.

---

## lot_requirements

Yêu cầu chi tiết **do AI trích xuất** từ tài liệu mời thầu gốc (PDF) — dữ liệu không có sẵn trong CSV/TED có
cấu trúc (số tiền bảo lãnh cụ thể, số lượng dự án tham chiếu, chứng chỉ bắt buộc...). Lưu kèm trích đoạn + số
trang để (1) tái sử dụng cho nhiều công ty mà không trích xuất lại, (2) làm bằng chứng cho `verdicts`.

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `lot_id` | UUID (FK → lots, `ON DELETE CASCADE`) | ✔ | |
| `requirement_type` | TEXT | ✔ | vd `'guarantee_amount'`, `'reference_project_count'`, `'reference_project_value'`, `'certification'`, `'construction_deadline'`, `'insurance'`, `'other'` |
| `requirement_value_text` | TEXT | | Giá trị dạng mô tả, vd `'3 dự án tương tự trong 5 năm gần nhất'` |
| `requirement_value_numeric` | NUMERIC(18,2) | | Giá trị dạng số nếu parse được, để so trực tiếp (vd với `companies.guarantee_ceiling`) |
| `requirement_unit` | TEXT | | Đơn vị của `requirement_value_numeric` — `'EUR'`, `'months'`, `'count'`... |
| `source_excerpt` | TEXT | ✔ | Trích đoạn nguyên văn từ tài liệu — bằng chứng cho giá trị trích xuất |
| `source_page` | INTEGER | | Số trang trong tài liệu gốc |
| `source_document_url` | TEXT | | Link/đường dẫn tài liệu đã trích xuất |
| `extraction_model` | TEXT | | Tên model AI đã dùng, vd `'claude-sonnet-5'` |
| `extraction_confidence` | NUMERIC(3,2) | | Độ tin cậy tự đánh giá của model (0.00–1.00) |
| `extracted_at` | TIMESTAMPTZ | ✔ | `now()` |

**Index:** `lot_id`, `requirement_type`.

---

## lot_award_results

Kết quả/lịch sử trúng thầu của 1 lot (nếu đã diễn ra). Map từ `tender.csv` (hồ sơ dự thầu đã nộp — **không phải
"tender = gói thầu"** theo nghĩa bài toán, xem ghi chú ở bảng `tenders`), `procedureLotResult.csv`,
`contract.csv`, `receivedSubmissions.csv`, `organisation.csv` (role=`winner`). Hữu ích cho quy tắc quyết định
"gói đã có người trúng thầu → `HARD_FAIL`" và dữ liệu tham khảo mặt bằng giá thị trường.

| Cột | Kiểu | Bắt buộc | Nguồn CSV / Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `lot_id` | UUID (FK → lots, UNIQUE, `ON DELETE CASCADE`) | ✔ | Quan hệ 1:1 với lot |
| `winner_chosen` | TEXT | | `procedureLotResult.winnerChosen` — `'selec-w'` = đã chọn nhà thầu trúng, `'clos-nw'` = đóng gói không có người trúng |
| `not_awarded_reason` | TEXT | | `procedureLotResult.notAwardedReason` — vd `'all-rej'`, `'ins-fund'`, `'no-rece'` |
| `received_submissions_count` | INTEGER | | `receivedSubmissions.receivedSubmissionsCount` (type=`'tenders'`) |
| `winning_bid_value` | NUMERIC(18,2) | | `tender.tenderValue` (của hồ sơ dự thầu thắng) |
| `winning_bid_currency` | TEXT | | `tender.tenderValueCurrency` |
| `winner_organisation_name` | TEXT | | `organisation.organisationName` (role=`winner`) |
| `winner_size` | TEXT | | `organisation.winnerSize` — `'micro'`/`'small'`/`'medium'`/`'large'` |
| `winner_decision_date` | TIMESTAMPTZ | | `contract.winnerDecisionDate` |
| `contract_conclusion_date` | TIMESTAMPTZ | | `contract.contractConclusionDate` |
| `created_at` | TIMESTAMPTZ | ✔ | `now()` |

**Quy tắc gợi ý:** `winner_chosen = 'selec-w'` → engine nên tự động `HARD_FAIL` mọi công ty cho lot này (gói đã
đóng, không còn nhận hồ sơ).

---

## verdicts

Kết quả đánh giá 1 công ty với 1 lot cụ thể. **Append-only** — không `UPDATE`, mỗi lần engine chạy lại thì
`INSERT` dòng mới để giữ lịch sử.

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `id` | UUID (PK) | ✔ | `gen_random_uuid()` |
| `company_id` | UUID (FK → companies, `ON DELETE CASCADE`) | ✔ | |
| `tender_id` | UUID (FK → tenders, `ON DELETE CASCADE`) | ✔ | Denormalized để query nhanh cấp gói mà không cần join qua `lots` |
| `lot_id` | UUID (FK → lots, `ON DELETE CASCADE`) | ✔ | **Luôn NOT NULL** — mọi tender đã có ≥1 lot nên không cần NULL đại diện "cấp gói" |
| `verdict` | `verdict_type` | ✔ | `HARD_FAIL` / `FLAG` / `CANDIDATE` |
| `constraint_category` | TEXT | | Nhóm ràng buộc, vd `'region'`, `'contract_value'`, `'guarantee_limit'`, `'excluded_capability'`, `'missing_reference'`, `'availability'`, `'weekly_capacity'`, `'deadline'`, `'already_awarded'`, `'sme_eligibility'`. Không dùng ENUM cứng vì logic quyết định có thể mở rộng thêm loại ràng buộc |
| `reason` | TEXT | ✔ | Lý do cụ thể, ngôn ngữ tự nhiên, giải thích ràng buộc nào bị vi phạm/thoả mãn |
| `source_requirement_id` | UUID (FK → lot_requirements, `ON DELETE SET NULL`) | | Liên kết tới yêu cầu AI trích xuất làm căn cứ (nếu có) |
| `source_excerpt` | TEXT | | Trích đoạn nguồn (copy từ `lot_requirements` hoặc trích trực tiếp) |
| `source_page` | INTEGER | | Số trang tài liệu |
| `source_document_url` | TEXT | | Đường dẫn tài liệu gốc |
| `rule_version` | TEXT | | Phiên bản logic quyết định đã sinh ra verdict này — phục vụ tái lập/so sánh khi rule thay đổi |
| `evaluated_at` | TIMESTAMPTZ | ✔ | `now()` |

**Index:** `company_id`, `tender_id`, `lot_id`, `verdict`, `(company_id, lot_id, evaluated_at DESC)`.

---

## Function: great_circle_km

```sql
great_circle_km(lat1, lon1, lat2, lon2) RETURNS DOUBLE PRECISION
```

Khoảng cách đường chim bay (km) giữa 2 toạ độ (công thức spherical law of cosines, không cần extension). Dùng
để kiểm tra `companies.region_radius_km` so với khoảng cách thực tới `lots.place_lat/place_lon`. Hàm là
`STRICT` — trả về `NULL` nếu bất kỳ toạ độ nào chưa geocode; tầng ứng dụng nên coi `NULL` là "chưa xác định
được khoảng cách" (→ `FLAG` để review thủ công), **không phải** "trong bán kính".

---

## Views

### `latest_verdicts`
Verdict mới nhất cho mỗi cặp `(company_id, lot_id)` — `SELECT DISTINCT ON (...) ... ORDER BY evaluated_at DESC`.
Dùng cho hầu hết truy vấn hiển thị thay vì query trực tiếp bảng `verdicts` (append-only, có thể có nhiều dòng
lịch sử cho cùng 1 cặp).

### `tender_verdict_summary`
Gộp verdict xấu nhất trong các lot con của 1 gói thành verdict đại diện cấp gói
(`HARD_FAIL` > `FLAG` > `CANDIDATE`), kèm số lượng lot theo từng loại verdict (`hard_fail_lot_count`,
`flag_lot_count`, `candidate_lot_count`) và `last_evaluated_at`.

---

## Nguồn dữ liệu chưa map / hạn chế đã biết

| Nguồn | Lý do chưa map |
|---|---|
| `changes.csv` | Lịch sử sửa đổi thông báo (thủ tục hành chính phụ) — không ảnh hưởng quyết định sàng lọc |
| `secondStage.csv` | Chi tiết vòng đàm phán/rút gọn ứng viên — chỉ áp dụng thủ tục hạn chế, ngoài phạm vi MVP |
| `cvdInformation.csv` | Dữ liệu xe sạch (Clean Vehicles Directive) — không liên quan xây dựng |
| `organisation.winnerOwnerNationality`, `winnerListed` | Chi tiết nhà thầu thắng, không cần cho luồng đánh giá công ty mới |
| `TED_17-09-2026.csv` (toàn bộ) | File digest hằng ngày, **không có khoá UUID chung** với các bảng eForms chi tiết còn lại trong bộ dữ liệu mẫu — 2 cột hữu ích nhất (`submission_deadline`, `notice_publication_number`) vẫn giữ trên `tenders` nhưng cần ETL đối chiếu tương đối (buyer + ngày đăng + CPV), không `JOIN` trực tiếp được |
| `companies.region_center_lat/lon`, `lots.place_lat/lon` | Cần bước geocode riêng (vd Nominatim/OpenStreetMap) trong ETL — Appendix A và dữ liệu nguồn chỉ có tên thành phố/mã NUTS, không có toạ độ. Cho tới khi geocode xong, `great_circle_km()` sẽ trả `NULL` |
| Số tiền bảo lãnh cụ thể, số lượng/loại reference yêu cầu, chứng chỉ bắt buộc | Không có trong dữ liệu CSV/API có cấu trúc — chỉ nằm trong PDF Vergabeunterlagen, cần AI đọc và trích xuất vào `lot_requirements` |
