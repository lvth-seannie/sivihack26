-- =====================================================================
-- SCHEMA: "Three Out of Forty" — SiviHack 2026 (sponsor: Arctis AI)
-- Hệ thống sàng lọc gói thầu xây dựng cho công ty ở Đức.
-- Target: PostgreSQL 15+ (Neon)
-- =====================================================================
--
-- NGUỒN DỮ LIỆU THẬT đã đối chiếu (backend/database/raw_data/):
--   notice.csv, procedure.csv, purpose.csv, lot.csv, classification.csv,
--   placeOfPerformance.csv, duration.csv, submissionTerms.csv,
--   additionalInformation.csv, strategicProcurement.csv, organisation.csv,
--   procedureLotResult.csv, receivedSubmissions.csv, tender.csv,
--   contract.csv, noticeResult.csv, changes.csv, secondStage.csv,
--   cvdInformation.csv, TED_17-09-2026.csv
--
-- Đây là dữ liệu xuất thô theo chuẩn eForms của TED (Tenders Electronic
-- Daily - cổng đấu thầu công khai EU), được chuẩn hoá (normalize) thành
-- ~19 bảng con theo từng "Business Term" của eForms. Điểm quan trọng
-- cần lưu ý khi đọc code bên dưới:
--   * "tender.csv" trong dữ liệu gốc KHÔNG PHẢI là "gói thầu" — đó là hồ
--     sơ DỰ THẦU đã nộp (giá trị bid, hạng, nhà thầu...) tức dữ liệu KẾT
--     QUẢ sau khi đấu thầu xong. Để tránh nhầm lẫn với khái niệm "tender
--     = gói thầu" trong bài toán, dữ liệu này được đưa vào bảng
--     lot_award_results (kết quả/lịch sử trúng thầu), KHÔNG map vào
--     bảng "tenders".
--   * Khái niệm "gói thầu" (tenders) trong bài toán tương ứng với 1
--     "notice" (thông báo mời thầu, khoá tự nhiên là noticeIdentifier +
--     noticeVersion), gộp từ notice.csv + procedure.csv + purpose.csv
--     (dòng không có lotIdentifier — đại diện cho toàn bộ gói) +
--     classification.csv (dòng không có lotIdentifier).
--   * Khái niệm "lot" (phần nhỏ đấu thầu riêng) tương ứng các dòng CÓ
--     lotIdentifier trong purpose/classification/placeOfPerformance/
--     duration/submissionTerms/additionalInformation/strategicProcurement.
--     Ngay cả gói thầu không chia lot cũng luôn có đúng 1 dòng lot ảo
--     "LOT-0000" phản ánh y hệt dữ liệu cấp gói — nên trong schema này
--     MỌI tender luôn có tối thiểu 1 lot, giúp việc so sánh công ty vs
--     lot là đủ để suy ra kết quả ở cấp gói (xem VIEW tender_verdict_summary
--     cuối file).
--   * Cột "Deadline for receipt of tenders" (hạn nộp hồ sơ thực tế) và
--     "Notice publication number" (số công báo OJEU, vd "639077-2026")
--     CHỈ tồn tại trong TED_17-09-2026.csv — đây là file "digest" hằng
--     ngày, KHÔNG có khoá UUID chung với các bảng eForms chi tiết còn
--     lại trong dữ liệu mẫu này. Vì vậy 2 cột này được giữ lại trên
--     bảng tenders nhưng phải nạp bằng bước ETL đối chiếu tương đối
--     (buyer + publication_date + CPV), không JOIN trực tiếp được.
--   * Không có cột nào trong dữ liệu gốc cho biết SỐ TIỀN bảo lãnh yêu
--     cầu (chỉ có cờ true/false "guaranteeRequired") hay các yêu cầu chi
--     tiết khác (số lượng reference dự án, chứng chỉ...). Những thông
--     tin này chỉ có trong tài liệu mời thầu (PDF Vergabeunterlagen)
--     gắn với từng gói/lot, cần AI trích xuất kèm trích đoạn + số trang
--     — đây là lý do bảng lot_requirements được thêm vào (xem bên dưới).
-- =====================================================================


-- gen_random_uuid() có sẵn trong core từ Postgres 13+ (Neon dùng bản mới
-- hơn nên không bắt buộc), nhưng bật pgcrypto để chắc chắn tương thích
-- nếu chạy trên phiên bản Postgres cũ hơn.
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ---------------------------------------------------------------------
-- ENUM: phán quyết sàng lọc
-- ---------------------------------------------------------------------
CREATE TYPE verdict_type AS ENUM ('HARD_FAIL', 'FLAG', 'CANDIDATE');
COMMENT ON TYPE verdict_type IS
  'HARD_FAIL = loại thẳng do vi phạm ràng buộc cứng; '
  'FLAG = rủi ro nhưng còn tranh luận được, cần review thủ công; '
  'CANDIDATE = đạt các ràng buộc đã kiểm tra, có thể tham gia đấu thầu.';


-- =====================================================================
-- BẢNG: buyers — Bên mời thầu (Auftraggeber)
-- =====================================================================
-- Tách riêng khỏi tenders để tránh lặp dữ liệu (1 buyer đăng nhiều gói),
-- và vì organisation.csv gốc lưu buyer/reviewer/winner chung 1 bảng theo
-- role — ở đây ta chỉ giữ lại các dòng organisationRole = 'buyer'.
-- Không có trong khung ban đầu của yêu cầu, nhưng thêm vào vì dữ liệu
-- CSV thật lặp lại thông tin bên mời thầu ở mỗi notice — nếu nhét thẳng
-- vào bảng tenders sẽ trùng lặp không cần thiết.
CREATE TABLE buyers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_identifier TEXT UNIQUE,               -- organisation.organisationIdentifier (mã định danh pháp nhân, vd "11-1393306000-19")
    name                    TEXT NOT NULL,              -- organisation.organisationName
    city                    TEXT,                       -- organisation.organisationCity
    post_code               TEXT,                       -- organisation.organisationPostCode
    country_subdivision     TEXT,                       -- organisation.organisationCountrySubdivision (mã NUTS, vd "DE300")
    country_code            TEXT,                       -- organisation.organisationCountryCode (vd "DEU")
    website                 TEXT,                       -- organisation.organisationInternetAddress
    legal_type              TEXT,                       -- organisation.buyerLegalType (vd omu-lbeh, koerp-oer-kommun...)
    is_contracting_entity   BOOLEAN,                    -- organisation.buyerContractingEntity (true = ngành tiện ích/hạ tầng theo Directive 2014/25, false/NULL = cơ quan công quyền thường)
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE buyers IS 'Bên mời thầu (chủ đầu tư/cơ quan công quyền đăng gói thầu), dedup theo organisation_identifier.';


-- =====================================================================
-- BẢNG: companies — Công ty mẫu tham gia sàng lọc
-- =====================================================================
-- CẤU TRÚC NÀY LẤY THEO ĐÚNG Appendix A (dữ liệu mẫu 3 công ty) của đề
-- bài, thay cho khung NUTS-array ban đầu:
--   * Vùng hoạt động mô hình hoá theo "tâm vùng + bán kính" (region_center
--     + region_radius_km) — khớp đúng cách Appendix A mô tả (vd Augsburg,
--     bán kính 150km) — CHÍNH XÁC hơn nhiều so với so khớp theo mã NUTS,
--     vì khoảng cách thực tế tới công trường mới là ràng buộc thật của
--     nhà thầu xây dựng, không phải ranh giới hành chính.
--   * Kinh nghiệm/năng lực dùng chung 1 bộ "tag" tự do (references_held /
--     capabilities_excluded) thay vì mã CPV — vì Appendix A dùng nhãn
--     nghiệp vụ cụ thể (vd 'road_construction', 'high_voltage') dễ so
--     khớp trực tiếp với lots.required_capabilities (xem bảng lots) hơn
--     là mã CPV vốn chỉ mang tính hành chính/phân loại thống kê.
CREATE TABLE companies (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                      TEXT NOT NULL,

    -- Vùng hoạt động: tâm vùng (tên thành phố, theo Appendix A) + bán
    -- kính km công ty sẵn sàng di chuyển tới công trường. *_lat/*_lon
    -- KHÔNG có sẵn trong Appendix A (chỉ có tên thành phố) — cần geocode
    -- riêng lúc ETL (vd qua Nominatim/OpenStreetMap) rồi mới tính được
    -- khoảng cách thực; để NULL cho tới khi geocode xong. Dùng cùng với
    -- lots.place_lat/place_lon và hàm great_circle_km() ở cuối file.
    region_center              TEXT NOT NULL,             -- Appendix A: region_center (vd 'Augsburg')
    region_center_lat          NUMERIC(9,6),               -- geocode riêng, không có trong Appendix A
    region_center_lon          NUMERIC(9,6),               -- geocode riêng, không có trong Appendix A
    region_radius_km           INTEGER NOT NULL CHECK (region_radius_km > 0), -- Appendix A: region_radius_km

    -- Khoảng giá trị hợp đồng công ty CHẤP NHẬN đấu thầu — dùng để loại
    -- các gói quá nhỏ (không đáng làm) hoặc quá lớn (vượt năng lực).
    contract_min                NUMERIC(18,2),             -- Appendix A: contract_min
    contract_max                NUMERIC(18,2),             -- Appendix A: contract_max
    contract_currency           TEXT NOT NULL DEFAULT 'EUR',
    CHECK (contract_min IS NULL OR contract_max IS NULL OR contract_min <= contract_max),

    -- Hạn mức bảo lãnh (Bürgschaftsrahmen) tối đa công ty có thể cung
    -- cấp cho 1 hợp đồng — so sánh với số tiền bảo lãnh yêu cầu trích
    -- xuất được từ tài liệu mời thầu (xem lot_requirements). Có thể
    -- NULL khi công ty không khai trần cụ thể (vd Hanseatische Bau AG
    -- trong Appendix A — ràng buộc thật của họ nằm ở weekly_bid_capacity,
    -- không phải bảo lãnh) — engine cần xử lý NULL là "chưa biết, đừng
    -- HARD_FAIL chỉ vì thiếu dữ liệu", không phải "không giới hạn".
    guarantee_ceiling            NUMERIC(18,2),             -- Appendix A: guarantee_ceiling
    guarantee_currency           TEXT NOT NULL DEFAULT 'EUR',

    -- Năng lực/kinh nghiệm đã có, dạng tag tự do dùng chung vocabulary
    -- với lots.required_capabilities (vd 'road_construction',
    -- 'sewer_pipeline'). Dùng để: (1) CANDIDATE khi required_capabilities
    -- là tập con của references_held; (2) tính điểm phù hợp.
    references_held              TEXT[] NOT NULL DEFAULT '{}', -- Appendix A: references_held

    -- Năng lực KHÔNG có — nguồn chính tạo ra HARD_FAIL đặc thù theo
    -- từng công ty: nếu lots.required_capabilities giao với
    -- capabilities_excluded thì loại thẳng, bất kể các ràng buộc khác
    -- có đạt hay không. Đây là lý do kết quả phải thay đổi rõ rệt khi
    -- đổi công ty.
    capabilities_excluded        TEXT[] NOT NULL DEFAULT '{}', -- Appendix A: capabilities_excluded

    -- Ràng buộc vận hành (không có trong khung 4-bảng ban đầu, thêm theo
    -- đúng dữ liệu Appendix A):
    available_from               DATE,                      -- Appendix A: available_from — công ty chỉ nhận việc từ ngày này trở đi (NULL = sẵn sàng ngay); so với lots.duration_start_date để loại các gói cần khởi công trước ngày này
    weekly_bid_capacity          INTEGER CHECK (weekly_bid_capacity IS NULL OR weekly_bid_capacity > 0), -- KHÔNG có trong INSERT mẫu của Appendix A nhưng được đề bài gợi ý thêm cho Hanseatische Bau AG (ràng buộc thật của họ là năng lực đấu thầu ~3 tender/tuần, không phải trần bảo lãnh) — NULL = không giới hạn biết trước; dùng để FLAG khi công ty đã đạt số lượng CANDIDATE trong tuần

    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE companies IS 'Công ty mẫu (Đức) tham gia sàng lọc gói thầu — hồ sơ năng lực dùng làm đầu vào cho engine quyết định. Cấu trúc theo đúng Appendix A của đề bài.';
COMMENT ON COLUMN companies.region_radius_km IS 'Bán kính hoạt động (km) tính từ region_center — so khớp khoảng cách thực với lots.place_lat/place_lon qua great_circle_km().';
COMMENT ON COLUMN companies.capabilities_excluded IS 'Tag năng lực KHÔNG có — nguồn chính tạo ra HARD_FAIL đặc thù theo từng công ty.';
COMMENT ON COLUMN companies.weekly_bid_capacity IS 'Ràng buộc vận hành: số gói tối đa công ty có thể theo đuổi mỗi tuần — không có trong dữ liệu Appendix A gốc, thêm theo gợi ý của đề bài cho trường hợp Hanseatische Bau AG.';


-- =====================================================================
-- BẢNG: cpv_codes — Từ điển mã CPV (Common Procurement Vocabulary)
-- =====================================================================
-- Không có sẵn mô tả CPV trong raw_data (các bảng chỉ lưu mã số thô,
-- vd "45262100"); thêm bảng tra cứu này để UI/AI hiển thị mô tả CPV
-- thay vì mã số khó đọc, và hỗ trợ so khớp kinh nghiệm công ty theo
-- ngành nghề. Cần nạp dữ liệu từ danh mục CPV chính thức của EU (không
-- có trong raw_data) hoặc trích từ cột "Main classification" (dạng text)
-- trong TED_17-09-2026.csv trong lúc ETL. Không bắt buộc cho MVP nhưng
-- rẻ để có và hữu ích cho giải thích quyết định.
CREATE TABLE cpv_codes (
    code            TEXT PRIMARY KEY,      -- mã CPV 8 chữ số, vd '45262100'
    description_en  TEXT,
    description_de  TEXT
);
COMMENT ON TABLE cpv_codes IS 'Từ điển mã CPV (ngành nghề/hạng mục công trình theo chuẩn mua sắm công EU) — bảng tra cứu, nạp riêng ngoài raw_data.';


-- =====================================================================
-- BẢNG: tenders — Gói thầu (cấp "notice" / toàn bộ thủ tục mời thầu)
-- =====================================================================
CREATE TABLE tenders (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Khoá tự nhiên từ nguồn (dùng để ETL upsert idempotent qua
    -- ON CONFLICT). notice_version tồn tại vì 1 gói có thể có nhiều
    -- version thông báo (sửa đổi/huỷ...) theo thời gian.
    notice_identifier           UUID NOT NULL,           -- notice.noticeIdentifier
    notice_version               TEXT NOT NULL,           -- notice.noticeVersion
    procedure_identifier        UUID,                    -- notice.procedureIdentifier
    UNIQUE (notice_identifier, notice_version),

    buyer_id                    UUID REFERENCES buyers(id) ON DELETE SET NULL,

    title                        TEXT,                    -- purpose.title (dòng lotIdentifier IS NULL)
    description                  TEXT,                    -- purpose.description (dòng lotIdentifier IS NULL)
    main_nature                  TEXT CHECK (main_nature IN ('works', 'services', 'supplies') OR main_nature IS NULL), -- purpose.mainNature

    -- CPV chính của toàn gói (dòng lotIdentifier IS NULL trong classification.csv).
    -- Không đặt FK cứng tới cpv_codes.code vì cpv_codes chỉ là bảng tra
    -- cứu tuỳ chọn, nạp riêng và có thể chưa đầy đủ — không được để
    -- việc thiếu 1 mã CPV trong từ điển chặn việc ETL gói thầu thật.
    main_cpv_code                TEXT,                    -- classification.mainClassificationCode
    main_cpv_description         TEXT,                    -- fallback: text "Main classification" từ TED_*.csv khi chưa có trong cpv_codes

    estimated_value               NUMERIC(18,2),           -- purpose.estimatedValue (cấp gói, có thể NULL nếu chỉ khai theo từng lot)
    estimated_value_currency      TEXT DEFAULT 'EUR',      -- purpose.estimatedValueCurrency

    legal_basis                  TEXT,                    -- notice.procedureLegalBasis (vd '32014L0024', 'de-uvgo')
    procedure_type                TEXT,                    -- procedure.procedureType (vd 'open', 'de-open', 'neg-w-call'...) — không CHECK vì danh mục eForms có thể mở rộng theo thời gian
    procedure_accelerated        BOOLEAN,                 -- procedure.procedureAccelerated
    cross_border_law             TEXT,                    -- procedure.crossBorderLaw

    lots_max_allowed              INTEGER,                 -- procedure.lotsMaxAllowed — số lot tối đa 1 nhà thầu được nộp hồ sơ
    lots_all_required             BOOLEAN,                 -- procedure.lotsAllRequired — bắt buộc dự thầu tất cả các lot
    lots_max_awarded              INTEGER,                 -- procedure.lotsMaxAwarded

    notice_type                   TEXT,                    -- notice.noticeType (vd 'cn-standard', 'can-standard'...)
    form_type                     TEXT,                    -- notice.formType (vd 'competition', 'result', 'change'...)
    publication_date              TIMESTAMPTZ,             -- notice.publicationDate

    -- 2 cột dưới đây CHỈ có trong TED_17-09-2026.csv (file digest hằng
    -- ngày), không JOIN trực tiếp được qua UUID với các bảng eForms chi
    -- tiết — ETL cần đối chiếu tương đối (buyer + ngày đăng + CPV) hoặc
    -- để trống nếu không chắc chắn.
    notice_publication_number     TEXT,                    -- TED_*.csv "Notice publication number" (số công báo OJEU, vd '639077-2026')
    submission_deadline           TIMESTAMPTZ,             -- TED_*.csv "Deadline for receipt of tenders" (hạn nộp hồ sơ)

    source_document_url           TEXT,                    -- link công khai tới tài liệu mời thầu gốc (PDF Vergabeunterlagen) trên nguồn thu thập, dùng làm nguồn trích dẫn cho verdicts

    -- Nguồn thu thập gói thầu này (theo kế hoạch ETL: oeffentlichevergabe.de
    -- là nguồn chính, TED là nguồn dự phòng cho gói lớn hơn ngưỡng EU,
    -- service.bund.de chỉ để đối chiếu). Dùng để ưu tiên/khử trùng khi
    -- cùng 1 gói xuất hiện ở nhiều nguồn (match theo buyer + title +
    -- publication_date), và để biết nguồn nào đáng tin hơn khi dữ liệu
    -- mâu thuẫn.
    source_system                 TEXT CHECK (source_system IN ('oeffentlichevergabe', 'ted', 'service_bund') OR source_system IS NULL),

    -- Sau khi tải PDF tài liệu mời thầu về và lưu vào Backblaze B2 (bước
    -- xử lý offline, tốn thời gian nhất trong pipeline — nên batch trước
    -- demo), object key được ghi lại đây để tra cứu lại file gốc phục vụ
    -- AI trích xuất (ghi kết quả vào lots.required_capabilities,
    -- lots.guarantee_required, lots.duration_*, và lot_requirements).
    -- Khác với source_document_url (link công khai trên nguồn gốc):
    -- raw_document_key là khoá lưu trữ NỘI BỘ của hệ thống.
    raw_document_key              TEXT,

    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE tenders IS 'Gói thầu ở cấp toàn bộ thủ tục mời thầu (1 dòng = 1 notice). Luôn có >=1 lot con tương ứng (xem bảng lots).';
COMMENT ON COLUMN tenders.notice_publication_number IS 'Số công báo OJEU — chỉ có trong TED_*.csv, không có khoá chung với các bảng eForms chi tiết, cần ETL đối chiếu tương đối.';
COMMENT ON COLUMN tenders.raw_document_key IS 'Object key trong Backblaze B2 của PDF tài liệu mời thầu đã tải về — nguồn để AI trích xuất Eignungskriterien/Referenzen/Bürgschaft/Bauzeit/Lose.';


-- =====================================================================
-- BẢNG: lots — Từng phần nhỏ đấu thầu riêng biệt trong 1 gói thầu
-- =====================================================================
-- Đây là đơn vị chính để so sánh với company (mỗi gói không chia lot
-- vẫn có đúng 1 lot ảo "LOT-0000" — xem giải thích đầu file).
CREATE TABLE lots (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id                  UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    lot_identifier             TEXT NOT NULL,             -- lot.lotIdentifier (vd 'LOT-0000', 'LOT-0001'...)
    UNIQUE (tender_id, lot_identifier),

    internal_identifier        TEXT,                      -- purpose.internalIdentifier (mã nội bộ của bên mời thầu cho lot này)
    title                      TEXT,                      -- purpose.title (dòng có lotIdentifier)
    description                TEXT,                      -- purpose.description
    main_nature                TEXT CHECK (main_nature IN ('works', 'services', 'supplies') OR main_nature IS NULL), -- purpose.mainNature

    estimated_value             NUMERIC(18,2),             -- purpose.estimatedValue — giá trị dự kiến của RIÊNG lot này, dùng so khớp với companies.contract_min/contract_max
    estimated_value_currency    TEXT DEFAULT 'EUR',        -- purpose.estimatedValueCurrency

    main_cpv_code               TEXT,                      -- classification.mainClassificationCode (dòng có lotIdentifier) — giữ lại làm dữ liệu thô/tham khảo (không đặt FK cứng tới cpv_codes, xem lý do ở bảng tenders)
    additional_cpv_codes        TEXT[] NOT NULL DEFAULT '{}',      -- classification.additionalClassificationCodes (tách theo dấu phẩy)

    -- Tag năng lực mà lot này yêu cầu, cùng vocabulary tự do với
    -- companies.references_held / companies.capabilities_excluded (vd
    -- 'road_construction', 'high_voltage'). KHÔNG có sẵn trong dữ liệu
    -- CSV/TED thô — do AI trích xuất từ mục "Eignungskriterien"/
    -- "Referenzen" trong tài liệu mời thầu (kết hợp suy luận từ CPV +
    -- mô tả lot). Đây là cột chính driving HARD_FAIL/CANDIDATE theo
    -- năng lực, thay cho việc so khớp CPV thô kém chính xác hơn.
    required_capabilities       TEXT[] NOT NULL DEFAULT '{}',

    -- Nơi thực hiện hợp đồng — dùng so khớp vùng hoạt động của công ty.
    -- place_lat/place_lon KHÔNG có sẵn trong dữ liệu nguồn (chỉ có tên
    -- thành phố/mã NUTS) — cần geocode riêng lúc ETL để tính khoảng
    -- cách thực với companies.region_center_lat/lon qua great_circle_km().
    place_city                  TEXT,                      -- placeOfPerformance.placePerformanceCity
    place_post_code             TEXT,                      -- placeOfPerformance.placePerformancePostCode
    place_country_subdivision   TEXT,                      -- placeOfPerformance.placePerformanceCountrySubdivision (mã NUTS, vd 'DE300')
    place_country_code          TEXT,                      -- placeOfPerformance.placePerformanceCountryCode
    place_lat                   NUMERIC(9,6),               -- geocode riêng, không có trong dữ liệu nguồn
    place_lon                   NUMERIC(9,6),               -- geocode riêng, không có trong dữ liệu nguồn

    -- Thời hạn thi công (Bauzeit / construction_window) — so sánh với
    -- companies.available_from để loại các gói cần khởi công trước khi
    -- công ty rảnh.
    duration_start_date         DATE,                      -- duration.durationStartDate
    duration_end_date           DATE,                      -- duration.durationEndDate
    duration_period             NUMERIC,                   -- duration.durationPeriod (số lượng, đi kèm duration_period_unit)
    duration_period_unit        TEXT CHECK (duration_period_unit IN ('DAY','WEEK','MONTH','YEAR') OR duration_period_unit IS NULL), -- duration.durationPeriodUnit
    renewal_maximum             INTEGER,                   -- duration.renewalMaximum — số lần gia hạn tối đa

    -- Yêu cầu nộp hồ sơ. Lưu ý: guarantee_required chỉ là cờ true/false
    -- (KHÔNG có số tiền) — số tiền bảo lãnh cụ thể (nếu có) nằm ở
    -- lot_requirements.requirement_type = 'guarantee_amount'.
    tender_validity_deadline_days NUMERIC,                  -- submissionTerms.tenderValidityDeadline (đơn vị luôn là DAY trong dữ liệu mẫu — submissionTerms.tenderValidityDeadlineUnit)
    guarantee_required           BOOLEAN,                  -- submissionTerms.guaranteeRequired
    public_opening_date          TIMESTAMPTZ,              -- submissionTerms.publicOpeningDate

    suitable_for_smes            BOOLEAN,                  -- additionalInformation.suitableForSMEs
    strategic_procurement_flags  TEXT,                     -- strategicProcurement.strategicProcurement (vd 'none', 'env-imp,soc-obj') — thông tin ESG, không phải ràng buộc cứng nhưng có thể dùng cho FLAG

    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE lots IS 'Từng phần (lot) của 1 gói thầu — đơn vị chính để so sánh với hồ sơ công ty. Mọi tender luôn có tối thiểu 1 lot.';
COMMENT ON COLUMN lots.guarantee_required IS 'Chỉ là cờ true/false; số tiền bảo lãnh cụ thể (nếu trích xuất được từ tài liệu) nằm ở bảng lot_requirements.';


-- =====================================================================
-- BẢNG: lot_requirements — Yêu cầu chi tiết trích xuất bằng AI
-- =====================================================================
-- Dữ liệu CSV/TED chỉ có các trường "cứng" có cấu trúc (giá trị, vùng,
-- CPV, thời hạn...). Các yêu cầu chi tiết hơn (số tiền bảo lãnh cụ thể,
-- số lượng dự án tham chiếu yêu cầu, chứng chỉ bắt buộc...) chỉ nằm
-- trong tài liệu mời thầu gốc (PDF) và cần AI đọc + trích xuất. Bảng
-- này lưu lại lịch sử trích xuất đó kèm trích đoạn nguồn + số trang, để
-- (1) tái sử dụng cho nhiều công ty khác nhau mà không cần trích xuất
-- lại, và (2) làm nguồn trích dẫn (source_excerpt/source_page) mà
-- verdicts yêu cầu.
CREATE TABLE lot_requirements (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id                   UUID NOT NULL REFERENCES lots(id) ON DELETE CASCADE,

    requirement_type          TEXT NOT NULL,             -- vd 'guarantee_amount', 'reference_project_count', 'reference_project_value', 'certification', 'construction_deadline', 'insurance', 'other'
    requirement_value_text    TEXT,                      -- giá trị dạng mô tả, vd '3 dự án tương tự trong 5 năm gần nhất'
    requirement_value_numeric NUMERIC(18,2),              -- giá trị dạng số nếu parse được, để so sánh trực tiếp (vd với companies.guarantee_ceiling)
    requirement_unit          TEXT,                      -- đơn vị của requirement_value_numeric, vd 'EUR', 'months', 'count'

    source_excerpt             TEXT NOT NULL,             -- trích đoạn nguyên văn từ tài liệu, làm bằng chứng cho giá trị trích xuất
    source_page                INTEGER,                   -- số trang trong tài liệu gốc
    source_document_url        TEXT,                      -- link/đường dẫn tài liệu đã trích xuất (nên khớp lots.tender_id -> tenders.source_document_url nếu cùng nguồn)

    extraction_model           TEXT,                      -- tên model AI đã dùng để trích xuất, vd 'claude-sonnet-5'
    extraction_confidence      NUMERIC(3,2),              -- độ tin cậy tự đánh giá của model (0.00 - 1.00), có thể NULL
    extracted_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE lot_requirements IS 'Yêu cầu chi tiết trích xuất bằng AI từ tài liệu mời thầu gốc (không có sẵn trong dữ liệu CSV có cấu trúc), kèm trích đoạn + số trang làm bằng chứng.';


-- =====================================================================
-- BẢNG: lot_award_results — Kết quả/lịch sử trúng thầu (nếu đã có)
-- =====================================================================
-- Map từ tender.csv (hồ sơ dự thầu đã nộp — LƯU Ý: tên cột nguồn khác
-- với khái niệm "tender = gói thầu" trong bài toán, xem giải thích đầu
-- file), procedureLotResult.csv, contract.csv, receivedSubmissions.csv,
-- organisation.csv (role='winner'). Không có trong khung ban đầu nhưng
-- rất hữu ích: (1) quy tắc quyết định "gói đã có người trúng thầu ->
-- HARD_FAIL vì không còn nhận hồ sơ", (2) dữ liệu tham khảo mặt bằng
-- giá thị trường theo CPV/vùng.
CREATE TABLE lot_award_results (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id                       UUID NOT NULL UNIQUE REFERENCES lots(id) ON DELETE CASCADE,

    winner_chosen                 TEXT,                    -- procedureLotResult.winnerChosen: 'selec-w' = đã chọn nhà thầu trúng, 'clos-nw' = đóng gói không có người trúng
    not_awarded_reason            TEXT,                    -- procedureLotResult.notAwardedReason (vd 'all-rej', 'ins-fund', 'no-rece'...)

    received_submissions_count    INTEGER,                 -- receivedSubmissions.receivedSubmissionsCount (type='tenders')

    winning_bid_value             NUMERIC(18,2),           -- tender.tenderValue (của hồ sơ dự thầu thắng)
    winning_bid_currency          TEXT,                    -- tender.tenderValueCurrency
    winner_organisation_name      TEXT,                    -- organisation.organisationName (role='winner')
    winner_size                   TEXT,                    -- organisation.winnerSize ('micro'/'small'/'medium'/'large')

    winner_decision_date          TIMESTAMPTZ,             -- contract.winnerDecisionDate
    contract_conclusion_date      TIMESTAMPTZ,             -- contract.contractConclusionDate

    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE lot_award_results IS 'Kết quả trúng thầu lịch sử của 1 lot (nếu đã diễn ra). winner_chosen = ''selec-w'' nên được engine dùng để tự động HARD_FAIL (gói đã đóng, không còn nhận hồ sơ).';


-- =====================================================================
-- BẢNG: verdicts — Kết quả đánh giá sàng lọc (công ty x lot)
-- =====================================================================
-- Thiết kế append-only (không UPDATE): mỗi lần chạy engine quyết định
-- sẽ INSERT verdict mới, giữ lại lịch sử để audit/so sánh khi dữ liệu
-- công ty hoặc gói thầu thay đổi theo thời gian. Lấy verdict mới nhất
-- cho 1 cặp (company, lot) qua VIEW latest_verdicts bên dưới.
--
-- QUYẾT ĐỊNH THIẾT KẾ: gắn verdict vào lot_id (NOT NULL) thay vì cho
-- phép NULL để đại diện "cấp gói", vì mọi tender đã luôn có >=1 lot
-- (kể cả gói không chia lot có lot ảo LOT-0000) — nhờ vậy tránh được sự
-- mập mờ NULL = cấp gói vs NULL = chưa xác định. Verdict tổng hợp cấp
-- gói (nếu 1 gói có nhiều lot) được suy ra bằng VIEW, không lưu trùng.
CREATE TABLE verdicts (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                 UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tender_id                  UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    lot_id                      UUID NOT NULL REFERENCES lots(id) ON DELETE CASCADE,

    verdict                     verdict_type NOT NULL,

    -- Phân loại lý do để (1) hiển thị/lọc theo nhóm ràng buộc trên UI,
    -- (2) dễ dàng thấy điều gì THAY ĐỔI khi đổi công ty (yêu cầu quan
    -- trọng nhất của đề bài). Không dùng ENUM cứng vì logic quyết định
    -- có thể mở rộng thêm loại ràng buộc trong lúc phát triển hackathon.
    constraint_category         TEXT,                     -- vd 'region', 'contract_value', 'guarantee_limit', 'excluded_capability', 'missing_reference', 'availability', 'weekly_capacity', 'deadline', 'already_awarded', 'sme_eligibility'
    reason                       TEXT NOT NULL,             -- lý do cụ thể, ngôn ngữ tự nhiên, giải thích RÀNG BUỘC CỨNG nào bị vi phạm/thoả mãn

    -- Bằng chứng/nguồn trích dẫn — có thể lấy trực tiếp từ 1 dòng
    -- lot_requirements (qua source_requirement_id) hoặc do engine tự
    -- ghi thẳng khi lý do dựa trên dữ liệu có cấu trúc (vd so sánh số,
    -- không cần trích đoạn văn bản).
    source_requirement_id       UUID REFERENCES lot_requirements(id) ON DELETE SET NULL,
    source_excerpt               TEXT,                     -- trích đoạn nguồn (nếu có, copy từ lot_requirements hoặc trích trực tiếp)
    source_page                  INTEGER,                   -- số trang tài liệu (nếu có)
    source_document_url          TEXT,                      -- đường dẫn tài liệu gốc

    rule_version                 TEXT,                      -- phiên bản logic quyết định đã sinh ra verdict này, phục vụ tái lập/so sánh khi rule thay đổi
    evaluated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE verdicts IS 'Kết quả đánh giá 1 công ty với 1 lot cụ thể: HARD_FAIL/FLAG/CANDIDATE kèm lý do và trích dẫn nguồn. Bảng append-only, dùng VIEW latest_verdicts để lấy kết quả mới nhất.';
COMMENT ON COLUMN verdicts.constraint_category IS 'Nhóm ràng buộc bị đánh giá — dùng để thấy rõ điều gì thay đổi khi đổi công ty cho cùng 1 lot.';


-- =====================================================================
-- INDEX
-- =====================================================================
CREATE INDEX idx_tenders_buyer_id            ON tenders (buyer_id);
CREATE INDEX idx_tenders_main_cpv_code       ON tenders (main_cpv_code);
CREATE INDEX idx_tenders_publication_date    ON tenders (publication_date);

CREATE INDEX idx_lots_tender_id              ON lots (tender_id);
CREATE INDEX idx_lots_main_cpv_code          ON lots (main_cpv_code);
CREATE INDEX idx_lots_place_country_subdivision ON lots (place_country_subdivision);
CREATE INDEX idx_lots_estimated_value        ON lots (estimated_value);
CREATE INDEX idx_lots_place_lat_lon          ON lots (place_lat, place_lon); -- lọc thô trước khi tính great_circle_km() chính xác

CREATE INDEX idx_lot_requirements_lot_id     ON lot_requirements (lot_id);
CREATE INDEX idx_lot_requirements_type       ON lot_requirements (requirement_type);

CREATE INDEX idx_verdicts_company_id         ON verdicts (company_id);
CREATE INDEX idx_verdicts_tender_id          ON verdicts (tender_id);
CREATE INDEX idx_verdicts_lot_id             ON verdicts (lot_id);
CREATE INDEX idx_verdicts_verdict            ON verdicts (verdict);
CREATE INDEX idx_verdicts_company_lot_evaluated ON verdicts (company_id, lot_id, evaluated_at DESC); -- phục vụ VIEW latest_verdicts

-- GIN index cho các cột mảng hay dùng trong so khớp overlap (&&, @>, <@)
CREATE INDEX idx_companies_references_held      ON companies USING GIN (references_held);
CREATE INDEX idx_companies_capabilities_excluded ON companies USING GIN (capabilities_excluded);
CREATE INDEX idx_lots_required_capabilities     ON lots USING GIN (required_capabilities);
CREATE INDEX idx_lots_additional_cpv_codes      ON lots USING GIN (additional_cpv_codes);


-- =====================================================================
-- FUNCTION: great_circle_km — khoảng cách đường chim bay giữa 2 toạ độ
-- =====================================================================
-- Dùng để so khớp companies.region_center_lat/lon + region_radius_km với
-- lots.place_lat/lon — ràng buộc vùng hoạt động thực tế theo Appendix A
-- (vd 'Augsburg, bán kính 150km'), chính xác hơn nhiều so với so khớp
-- theo mã NUTS/tên thành phố. Trả về NULL nếu bất kỳ toạ độ nào chưa
-- geocode (STRICT) — tầng ứng dụng nên coi NULL là "chưa xác định được
-- khoảng cách" (FLAG để review thủ công), không phải "trong bán kính".
CREATE OR REPLACE FUNCTION great_circle_km(
    lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
    SELECT 6371 * acos(
        LEAST(1.0, GREATEST(-1.0,
            sin(radians(lat1)) * sin(radians(lat2))
            + cos(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
        ))
    );
$$ LANGUAGE sql IMMUTABLE STRICT;
COMMENT ON FUNCTION great_circle_km IS 'Khoảng cách đường chim bay (km) giữa 2 toạ độ, dùng để kiểm tra companies.region_radius_km với lots.place_lat/place_lon. NULL nếu thiếu toạ độ.';


-- =====================================================================
-- VIEW: latest_verdicts — verdict mới nhất cho mỗi cặp (company, lot)
-- =====================================================================
CREATE VIEW latest_verdicts AS
SELECT DISTINCT ON (company_id, lot_id) *
FROM verdicts
ORDER BY company_id, lot_id, evaluated_at DESC;
COMMENT ON VIEW latest_verdicts IS 'Verdict mới nhất cho mỗi cặp (công ty, lot) — dùng cho hầu hết truy vấn hiển thị thay vì query trực tiếp bảng verdicts (append-only).';


-- =====================================================================
-- VIEW: tender_verdict_summary — verdict tổng hợp cấp gói thầu
-- =====================================================================
-- Gộp verdict xấu nhất trong các lot của 1 gói làm verdict đại diện cấp
-- gói (HARD_FAIL > FLAG > CANDIDATE), phục vụ yêu cầu "so sánh công ty
-- với từng tender (và từng lot nếu có)" mà không cần lưu trùng dữ liệu.
CREATE VIEW tender_verdict_summary AS
SELECT
    lv.company_id,
    lv.tender_id,
    (ARRAY_AGG(lv.verdict ORDER BY
        CASE lv.verdict
            WHEN 'HARD_FAIL' THEN 0
            WHEN 'FLAG' THEN 1
            WHEN 'CANDIDATE' THEN 2
        END
    ))[1] AS overall_verdict,
    COUNT(*) FILTER (WHERE lv.verdict = 'HARD_FAIL') AS hard_fail_lot_count,
    COUNT(*) FILTER (WHERE lv.verdict = 'FLAG')      AS flag_lot_count,
    COUNT(*) FILTER (WHERE lv.verdict = 'CANDIDATE') AS candidate_lot_count,
    MAX(lv.evaluated_at) AS last_evaluated_at
FROM latest_verdicts lv
GROUP BY lv.company_id, lv.tender_id;
COMMENT ON VIEW tender_verdict_summary IS 'Verdict tổng hợp cấp gói thầu = verdict xấu nhất trong các lot con (HARD_FAIL > FLAG > CANDIDATE).';
