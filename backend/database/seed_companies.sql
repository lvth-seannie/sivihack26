-- =====================================================================
-- SEED: 3 công ty mẫu — Appendix A
-- =====================================================================
-- Khớp đúng cấu trúc bảng companies trong schema.sql (region_center +
-- region_radius_km thay cho NUTS-array; references_held/capabilities_excluded
-- thay cho CPV-array). Chưa geocode region_center -> region_center_lat/lon
-- (không có trong Appendix A) — để NULL, việc so khớp bán kính hoạt động
-- qua great_circle_km() sẽ chưa chạy được cho tới khi có bước geocode
-- riêng (vd Nominatim) trong ETL.
--
-- weekly_bid_capacity: KHÔNG có trong Appendix A gốc, nhưng đề bài gợi ý
-- thêm cho Hanseatische Bau AG vì ràng buộc thật của họ là năng lực đấu
-- thầu (~3 tender/tuần) chứ không phải trần bảo lãnh (guarantee_ceiling
-- = NULL). 2 công ty còn lại để NULL (không giới hạn biết trước).

INSERT INTO companies
    (name, region_center, region_radius_km, contract_min, contract_max,
     guarantee_ceiling, references_held, capabilities_excluded, available_from,
     weekly_bid_capacity)
VALUES
(
    'Brenner & Sohn Tiefbau GmbH',
    'Augsburg', 150, 400000, 4000000, 1500000,
    ARRAY['road_construction', 'sewer_pipeline', 'earthworks', 'municipal_civil'],
    ARRAY['rail_side', 'bridges', 'outside_germany'],
    '2027-03-01',
    NULL
),
(
    'Elektro Vogtland GmbH',
    'Plauen', 200, 80000, 900000, 300000,
    ARRAY['electrical_installation', 'fire_alarm', 'building_automation'],
    ARRAY['high_voltage', 'explosion_protected', 'main_contractor_multitrade'],
    NULL,
    NULL
),
(
    'Hanseatische Bau AG',
    'Hamburg', 600, 8000000, 90000000, NULL,
    ARRAY['building_construction', 'turnkey_projects'],
    ARRAY['civil_engineering_lead', 'roads', 'sewers', 'bridges', 'southern_germany'],
    NULL,
    3
);
