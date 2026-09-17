--
-- PostgreSQL database dump
--

\restrict tZpbfMynuWr42FKzlW1k2AN9aoMrx2txltYGJzTOL34p73pityVvKfEiLHwxuSP

-- Dumped from database version 18.6 (6569466)
-- Dumped by pg_dump version 18.6 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: buyers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.buyers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organisation_identifier text,
    name text NOT NULL,
    city text,
    post_code text,
    country_subdivision text,
    country_code text,
    website text,
    legal_type text,
    is_contracting_entity boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.buyers OWNER TO neondb_owner;

--
-- Name: TABLE buyers; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.buyers IS 'Bên mời thầu (chủ đầu tư/cơ quan công quyền đăng gói thầu), dedup theo organisation_identifier.';


--
-- Name: companies; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.companies (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    region_center text NOT NULL,
    region_center_lat numeric(9,6),
    region_center_lon numeric(9,6),
    region_radius_km integer NOT NULL,
    contract_min numeric(18,2),
    contract_max numeric(18,2),
    contract_currency text DEFAULT 'EUR'::text NOT NULL,
    guarantee_ceiling numeric(18,2),
    guarantee_currency text DEFAULT 'EUR'::text NOT NULL,
    references_held text[] DEFAULT '{}'::text[] NOT NULL,
    capabilities_excluded text[] DEFAULT '{}'::text[] NOT NULL,
    available_from date,
    weekly_bid_capacity integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT companies_check CHECK (((contract_min IS NULL) OR (contract_max IS NULL) OR (contract_min <= contract_max))),
    CONSTRAINT companies_region_radius_km_check CHECK ((region_radius_km > 0)),
    CONSTRAINT companies_weekly_bid_capacity_check CHECK (((weekly_bid_capacity IS NULL) OR (weekly_bid_capacity > 0)))
);


ALTER TABLE public.companies OWNER TO neondb_owner;

--
-- Name: TABLE companies; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.companies IS 'Công ty mẫu (Đức) tham gia sàng lọc gói thầu — hồ sơ năng lực dùng làm đầu vào cho engine quyết định. Cấu trúc theo đúng Appendix A của đề bài.';


--
-- Name: COLUMN companies.region_radius_km; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.companies.region_radius_km IS 'Bán kính hoạt động (km) tính từ region_center — so khớp khoảng cách thực với lots.place_lat/place_lon qua great_circle_km().';


--
-- Name: COLUMN companies.capabilities_excluded; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.companies.capabilities_excluded IS 'Tag năng lực KHÔNG có — nguồn chính tạo ra HARD_FAIL đặc thù theo từng công ty.';


--
-- Name: COLUMN companies.weekly_bid_capacity; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.companies.weekly_bid_capacity IS 'Ràng buộc vận hành: số gói tối đa công ty có thể theo đuổi mỗi tuần — không có trong dữ liệu Appendix A gốc, thêm theo gợi ý của đề bài cho trường hợp Hanseatische Bau AG.';


--
-- Name: cpv_codes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.cpv_codes (
    code text NOT NULL,
    description_en text,
    description_de text
);


ALTER TABLE public.cpv_codes OWNER TO neondb_owner;

--
-- Name: TABLE cpv_codes; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.cpv_codes IS 'Từ điển mã CPV (ngành nghề/hạng mục công trình theo chuẩn mua sắm công EU) — bảng tra cứu, nạp riêng ngoài raw_data.';


--
-- Name: verdicts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.verdicts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid NOT NULL,
    tender_id uuid NOT NULL,
    lot_id uuid NOT NULL,
    verdict public.verdict_type NOT NULL,
    constraint_category text,
    reason text NOT NULL,
    source_requirement_id uuid,
    source_excerpt text,
    source_page integer,
    source_document_url text,
    rule_version text,
    evaluated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.verdicts OWNER TO neondb_owner;

--
-- Name: TABLE verdicts; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.verdicts IS 'Kết quả đánh giá 1 công ty với 1 lot cụ thể: HARD_FAIL/FLAG/CANDIDATE kèm lý do và trích dẫn nguồn. Bảng append-only, dùng VIEW latest_verdicts để lấy kết quả mới nhất.';


--
-- Name: COLUMN verdicts.constraint_category; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.verdicts.constraint_category IS 'Nhóm ràng buộc bị đánh giá — dùng để thấy rõ điều gì thay đổi khi đổi công ty cho cùng 1 lot.';


--
-- Name: latest_verdicts; Type: VIEW; Schema: public; Owner: neondb_owner
--

CREATE VIEW public.latest_verdicts AS
 SELECT DISTINCT ON (company_id, lot_id) id,
    company_id,
    tender_id,
    lot_id,
    verdict,
    constraint_category,
    reason,
    source_requirement_id,
    source_excerpt,
    source_page,
    source_document_url,
    rule_version,
    evaluated_at
   FROM public.verdicts
  ORDER BY company_id, lot_id, evaluated_at DESC;


ALTER VIEW public.latest_verdicts OWNER TO neondb_owner;

--
-- Name: VIEW latest_verdicts; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON VIEW public.latest_verdicts IS 'Verdict mới nhất cho mỗi cặp (công ty, lot) — dùng cho hầu hết truy vấn hiển thị thay vì query trực tiếp bảng verdicts (append-only).';


--
-- Name: lot_award_results; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.lot_award_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    lot_id uuid NOT NULL,
    winner_chosen text,
    not_awarded_reason text,
    received_submissions_count integer,
    winning_bid_value numeric(18,2),
    winning_bid_currency text,
    winner_organisation_name text,
    winner_size text,
    winner_decision_date timestamp with time zone,
    contract_conclusion_date timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.lot_award_results OWNER TO neondb_owner;

--
-- Name: TABLE lot_award_results; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.lot_award_results IS 'Kết quả trúng thầu lịch sử của 1 lot (nếu đã diễn ra). winner_chosen = ''selec-w'' nên được engine dùng để tự động HARD_FAIL (gói đã đóng, không còn nhận hồ sơ).';


--
-- Name: lot_requirements; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.lot_requirements (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    lot_id uuid NOT NULL,
    requirement_type text NOT NULL,
    requirement_value_text text,
    requirement_value_numeric numeric(18,2),
    requirement_unit text,
    source_excerpt text NOT NULL,
    source_page integer,
    source_document_url text,
    extraction_model text,
    extraction_confidence numeric(3,2),
    extracted_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.lot_requirements OWNER TO neondb_owner;

--
-- Name: TABLE lot_requirements; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.lot_requirements IS 'Yêu cầu chi tiết trích xuất bằng AI từ tài liệu mời thầu gốc (không có sẵn trong dữ liệu CSV có cấu trúc), kèm trích đoạn + số trang làm bằng chứng.';


--
-- Name: lots; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.lots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tender_id uuid NOT NULL,
    lot_identifier text NOT NULL,
    internal_identifier text,
    title text,
    description text,
    main_nature text,
    estimated_value numeric(18,2),
    estimated_value_currency text DEFAULT 'EUR'::text,
    main_cpv_code text,
    additional_cpv_codes text[] DEFAULT '{}'::text[] NOT NULL,
    required_capabilities text[] DEFAULT '{}'::text[] NOT NULL,
    place_city text,
    place_post_code text,
    place_country_subdivision text,
    place_country_code text,
    place_lat numeric(9,6),
    place_lon numeric(9,6),
    duration_start_date date,
    duration_end_date date,
    duration_period numeric,
    duration_period_unit text,
    renewal_maximum integer,
    tender_validity_deadline_days numeric,
    guarantee_required boolean,
    public_opening_date timestamp with time zone,
    suitable_for_smes boolean,
    strategic_procurement_flags text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lots_duration_period_unit_check CHECK (((duration_period_unit = ANY (ARRAY['DAY'::text, 'WEEK'::text, 'MONTH'::text, 'YEAR'::text])) OR (duration_period_unit IS NULL))),
    CONSTRAINT lots_main_nature_check CHECK (((main_nature = ANY (ARRAY['works'::text, 'services'::text, 'supplies'::text])) OR (main_nature IS NULL)))
);


ALTER TABLE public.lots OWNER TO neondb_owner;

--
-- Name: TABLE lots; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.lots IS 'Từng phần (lot) của 1 gói thầu — đơn vị chính để so sánh với hồ sơ công ty. Mọi tender luôn có tối thiểu 1 lot.';


--
-- Name: COLUMN lots.guarantee_required; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.lots.guarantee_required IS 'Chỉ là cờ true/false; số tiền bảo lãnh cụ thể (nếu trích xuất được từ tài liệu) nằm ở bảng lot_requirements.';


--
-- Name: tender_verdict_summary; Type: VIEW; Schema: public; Owner: neondb_owner
--

CREATE VIEW public.tender_verdict_summary AS
 SELECT company_id,
    tender_id,
    (array_agg(verdict ORDER BY
        CASE verdict
            WHEN 'HARD_FAIL'::public.verdict_type THEN 0
            WHEN 'FLAG'::public.verdict_type THEN 1
            WHEN 'CANDIDATE'::public.verdict_type THEN 2
            ELSE NULL::integer
        END))[1] AS overall_verdict,
    count(*) FILTER (WHERE (verdict = 'HARD_FAIL'::public.verdict_type)) AS hard_fail_lot_count,
    count(*) FILTER (WHERE (verdict = 'FLAG'::public.verdict_type)) AS flag_lot_count,
    count(*) FILTER (WHERE (verdict = 'CANDIDATE'::public.verdict_type)) AS candidate_lot_count,
    max(evaluated_at) AS last_evaluated_at
   FROM public.latest_verdicts lv
  GROUP BY company_id, tender_id;


ALTER VIEW public.tender_verdict_summary OWNER TO neondb_owner;

--
-- Name: VIEW tender_verdict_summary; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON VIEW public.tender_verdict_summary IS 'Verdict tổng hợp cấp gói thầu = verdict xấu nhất trong các lot con (HARD_FAIL > FLAG > CANDIDATE).';


--
-- Name: tenders; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.tenders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    notice_identifier uuid NOT NULL,
    notice_version text NOT NULL,
    procedure_identifier uuid,
    buyer_id uuid,
    title text,
    description text,
    main_nature text,
    main_cpv_code text,
    main_cpv_description text,
    estimated_value numeric(18,2),
    estimated_value_currency text DEFAULT 'EUR'::text,
    legal_basis text,
    procedure_type text,
    procedure_accelerated boolean,
    cross_border_law text,
    lots_max_allowed integer,
    lots_all_required boolean,
    lots_max_awarded integer,
    notice_type text,
    form_type text,
    publication_date timestamp with time zone,
    notice_publication_number text,
    submission_deadline timestamp with time zone,
    source_document_url text,
    source_system text,
    raw_document_key text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tenders_main_nature_check CHECK (((main_nature = ANY (ARRAY['works'::text, 'services'::text, 'supplies'::text])) OR (main_nature IS NULL))),
    CONSTRAINT tenders_source_system_check CHECK (((source_system = ANY (ARRAY['oeffentlichevergabe'::text, 'ted'::text, 'service_bund'::text])) OR (source_system IS NULL)))
);


ALTER TABLE public.tenders OWNER TO neondb_owner;

--
-- Name: TABLE tenders; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON TABLE public.tenders IS 'Gói thầu ở cấp toàn bộ thủ tục mời thầu (1 dòng = 1 notice). Luôn có >=1 lot con tương ứng (xem bảng lots).';


--
-- Name: COLUMN tenders.notice_publication_number; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.tenders.notice_publication_number IS 'Số công báo OJEU — chỉ có trong TED_*.csv, không có khoá chung với các bảng eForms chi tiết, cần ETL đối chiếu tương đối.';


--
-- Name: COLUMN tenders.raw_document_key; Type: COMMENT; Schema: public; Owner: neondb_owner
--

COMMENT ON COLUMN public.tenders.raw_document_key IS 'Object key trong Backblaze B2 của PDF tài liệu mời thầu đã tải về — nguồn để AI trích xuất Eignungskriterien/Referenzen/Bürgschaft/Bauzeit/Lose.';


--
-- Data for Name: buyers; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.buyers (id, organisation_identifier, name, city, post_code, country_subdivision, country_code, website, legal_type, is_contracting_entity, created_at) FROM stdin;
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.companies (id, name, region_center, region_center_lat, region_center_lon, region_radius_km, contract_min, contract_max, contract_currency, guarantee_ceiling, guarantee_currency, references_held, capabilities_excluded, available_from, weekly_bid_capacity, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: cpv_codes; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.cpv_codes (code, description_en, description_de) FROM stdin;
\.


--
-- Data for Name: lot_award_results; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.lot_award_results (id, lot_id, winner_chosen, not_awarded_reason, received_submissions_count, winning_bid_value, winning_bid_currency, winner_organisation_name, winner_size, winner_decision_date, contract_conclusion_date, created_at) FROM stdin;
\.


--
-- Data for Name: lot_requirements; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.lot_requirements (id, lot_id, requirement_type, requirement_value_text, requirement_value_numeric, requirement_unit, source_excerpt, source_page, source_document_url, extraction_model, extraction_confidence, extracted_at) FROM stdin;
\.


--
-- Data for Name: lots; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.lots (id, tender_id, lot_identifier, internal_identifier, title, description, main_nature, estimated_value, estimated_value_currency, main_cpv_code, additional_cpv_codes, required_capabilities, place_city, place_post_code, place_country_subdivision, place_country_code, place_lat, place_lon, duration_start_date, duration_end_date, duration_period, duration_period_unit, renewal_maximum, tender_validity_deadline_days, guarantee_required, public_opening_date, suitable_for_smes, strategic_procurement_flags, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tenders; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.tenders (id, notice_identifier, notice_version, procedure_identifier, buyer_id, title, description, main_nature, main_cpv_code, main_cpv_description, estimated_value, estimated_value_currency, legal_basis, procedure_type, procedure_accelerated, cross_border_law, lots_max_allowed, lots_all_required, lots_max_awarded, notice_type, form_type, publication_date, notice_publication_number, submission_deadline, source_document_url, source_system, raw_document_key, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: verdicts; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.verdicts (id, company_id, tender_id, lot_id, verdict, constraint_category, reason, source_requirement_id, source_excerpt, source_page, source_document_url, rule_version, evaluated_at) FROM stdin;
\.


--
-- Name: buyers buyers_organisation_identifier_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.buyers
    ADD CONSTRAINT buyers_organisation_identifier_key UNIQUE (organisation_identifier);


--
-- Name: buyers buyers_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.buyers
    ADD CONSTRAINT buyers_pkey PRIMARY KEY (id);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: cpv_codes cpv_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.cpv_codes
    ADD CONSTRAINT cpv_codes_pkey PRIMARY KEY (code);


--
-- Name: lot_award_results lot_award_results_lot_id_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_award_results
    ADD CONSTRAINT lot_award_results_lot_id_key UNIQUE (lot_id);


--
-- Name: lot_award_results lot_award_results_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_award_results
    ADD CONSTRAINT lot_award_results_pkey PRIMARY KEY (id);


--
-- Name: lot_requirements lot_requirements_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_requirements
    ADD CONSTRAINT lot_requirements_pkey PRIMARY KEY (id);


--
-- Name: lots lots_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lots
    ADD CONSTRAINT lots_pkey PRIMARY KEY (id);


--
-- Name: lots lots_tender_id_lot_identifier_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lots
    ADD CONSTRAINT lots_tender_id_lot_identifier_key UNIQUE (tender_id, lot_identifier);


--
-- Name: tenders tenders_notice_identifier_notice_version_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT tenders_notice_identifier_notice_version_key UNIQUE (notice_identifier, notice_version);


--
-- Name: tenders tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT tenders_pkey PRIMARY KEY (id);


--
-- Name: verdicts verdicts_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verdicts
    ADD CONSTRAINT verdicts_pkey PRIMARY KEY (id);


--
-- Name: idx_companies_capabilities_excluded; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_companies_capabilities_excluded ON public.companies USING gin (capabilities_excluded);


--
-- Name: idx_companies_references_held; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_companies_references_held ON public.companies USING gin (references_held);


--
-- Name: idx_lot_requirements_lot_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lot_requirements_lot_id ON public.lot_requirements USING btree (lot_id);


--
-- Name: idx_lot_requirements_type; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lot_requirements_type ON public.lot_requirements USING btree (requirement_type);


--
-- Name: idx_lots_additional_cpv_codes; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_additional_cpv_codes ON public.lots USING gin (additional_cpv_codes);


--
-- Name: idx_lots_estimated_value; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_estimated_value ON public.lots USING btree (estimated_value);


--
-- Name: idx_lots_main_cpv_code; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_main_cpv_code ON public.lots USING btree (main_cpv_code);


--
-- Name: idx_lots_place_country_subdivision; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_place_country_subdivision ON public.lots USING btree (place_country_subdivision);


--
-- Name: idx_lots_place_lat_lon; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_place_lat_lon ON public.lots USING btree (place_lat, place_lon);


--
-- Name: idx_lots_required_capabilities; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_required_capabilities ON public.lots USING gin (required_capabilities);


--
-- Name: idx_lots_tender_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_lots_tender_id ON public.lots USING btree (tender_id);


--
-- Name: idx_tenders_buyer_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_tenders_buyer_id ON public.tenders USING btree (buyer_id);


--
-- Name: idx_tenders_main_cpv_code; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_tenders_main_cpv_code ON public.tenders USING btree (main_cpv_code);


--
-- Name: idx_tenders_publication_date; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_tenders_publication_date ON public.tenders USING btree (publication_date);


--
-- Name: idx_verdicts_company_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_verdicts_company_id ON public.verdicts USING btree (company_id);


--
-- Name: idx_verdicts_company_lot_evaluated; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_verdicts_company_lot_evaluated ON public.verdicts USING btree (company_id, lot_id, evaluated_at DESC);


--
-- Name: idx_verdicts_lot_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_verdicts_lot_id ON public.verdicts USING btree (lot_id);


--
-- Name: idx_verdicts_tender_id; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_verdicts_tender_id ON public.verdicts USING btree (tender_id);


--
-- Name: idx_verdicts_verdict; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_verdicts_verdict ON public.verdicts USING btree (verdict);


--
-- Name: lot_award_results lot_award_results_lot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_award_results
    ADD CONSTRAINT lot_award_results_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lots(id) ON DELETE CASCADE;


--
-- Name: lot_requirements lot_requirements_lot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lot_requirements
    ADD CONSTRAINT lot_requirements_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lots(id) ON DELETE CASCADE;


--
-- Name: lots lots_tender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.lots
    ADD CONSTRAINT lots_tender_id_fkey FOREIGN KEY (tender_id) REFERENCES public.tenders(id) ON DELETE CASCADE;


--
-- Name: tenders tenders_buyer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT tenders_buyer_id_fkey FOREIGN KEY (buyer_id) REFERENCES public.buyers(id) ON DELETE SET NULL;


--
-- Name: verdicts verdicts_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verdicts
    ADD CONSTRAINT verdicts_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: verdicts verdicts_lot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verdicts
    ADD CONSTRAINT verdicts_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lots(id) ON DELETE CASCADE;


--
-- Name: verdicts verdicts_source_requirement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verdicts
    ADD CONSTRAINT verdicts_source_requirement_id_fkey FOREIGN KEY (source_requirement_id) REFERENCES public.lot_requirements(id) ON DELETE SET NULL;


--
-- Name: verdicts verdicts_tender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verdicts
    ADD CONSTRAINT verdicts_tender_id_fkey FOREIGN KEY (tender_id) REFERENCES public.tenders(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict tZpbfMynuWr42FKzlW1k2AN9aoMrx2txltYGJzTOL34p73pityVvKfEiLHwxuSP

