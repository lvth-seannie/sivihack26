# Data Engineering — tasks cần làm ngay

Status: 2026-09-11 · Owner: Data Engineering · Audience: Backend, team

## Bối cảnh

ETL đang fail vì Supabase đụng trần **500 MB** (free tier). Các bảng chuẩn hoá
(`jobs`, `skills`, `job_skills_mapping`) bị rollback → hiện **rỗng**. Chỉ còn
`staging_jobs` (234k) và `candidates` (44k) có data.

Backend (nhánh `ai-career-nav`) đã sẵn sàng: `jobs_repo` query theo schema chuẩn,
endpoint fallback an toàn về stub khi bảng rỗng. **Chỉ chờ data.**

### Nguyên nhân gốc

| Vấn đề | Chi tiết |
|---|---|
| Dataset quá lớn & tạp | 234k job, đa số **non-tech** ("Engineering Project Coordinator", ".50 calibre heavy machinegun" là 1 "skill") |
| `skills` không dedup | 972,593 dòng, **0 dòng trùng**, 221 MB. 35k dòng > 60 ký tự, có dòng 3.643 ký tự, lỗi encoding (`Fran�ais`) |
| Giữ cả `staging_*` | `staging_jobs` + `staging_candidates` ≈ 167 MB, chỉ cần lúc transform |
| Hệ quả | Không đủ chỗ cho `job_skills_mapping` (234k job × ~12 skill ≈ 2.8M dòng ≈ 150-200 MB) |

---

## Task 1 — Lọc dataset về tech (quan trọng nhất, làm trước)

Trước khi transform `staging_jobs` → `jobs`, **chỉ giữ job liên quan tech**:

- Giữ nếu `job_title` khớp keyword:
  `engineer, developer, data, analyst, scientist, devops, sre, architect,
  programmer, software, ml, ai, backend, frontend, full stack, qa, cloud, security`
- HOẶC `job_skills` chứa ≥ 2 skill tech đã biết (Python, SQL, Java, AWS, React,
  Docker, Git, Kubernetes, TypeScript, ...)
- Mục tiêu: **~20–40k job** thay vì 234k.

Lợi ích kép: mọi bảng nhỏ đi 5–10 lần **và** số liệu Market Insights mới có ý nghĩa
(hiện `topRoles` toàn job non-tech).

---

## Task 2 — Clean + dedup `skills` khi transform

Tách `staging_jobs.job_skills` theo dấu phẩy. Với mỗi skill:

1. `TRIM`, gộp khoảng trắng thừa, chuẩn hoá **lowercase** (hoặc 1 dạng nhất quán).
2. **Loại bỏ** nếu:
   - dài > 60 ký tự
   - chứa cụm câu: `years of`, `degree in`, `ability to`, `experience with`,
     `bachelor`, `master`, `proficiency in`
   - toàn số / bắt đầu bằng số + đơn vị (`4+ years`, `.8 FTE`)
   - lỗi encoding (ký tự `�`)
3. **Dedup**:
   ```sql
   INSERT INTO skills (skill_name)
   SELECT DISTINCT lower(trim(s))
   FROM ( ... tách + lọc ở trên ... ) x(s)
   ON CONFLICT (skill_name) DO NOTHING;
   ```

Kỳ vọng: ~1M dòng → **~5–15k skill thật**.

---

## Task 3 — Nạp `job_skills_mapping` (mảnh còn thiếu)

Sau khi `jobs` + `skills` xong:

```sql
INSERT INTO job_skills_mapping (job_id, skill_id)
SELECT DISTINCT j.id, sk.id
FROM staging_jobs sj
JOIN jobs j
  ON j.title = sj.job_title            -- hoặc key bạn dùng để map staging -> jobs
JOIN LATERAL unnest(string_to_array(sj.job_skills, ',')) AS raw(skill) ON true
JOIN skills sk
  ON sk.skill_name = lower(trim(raw.skill))
ON CONFLICT DO NOTHING;
```

`topSkills`, chỉ số "AI/ML & cloud skill demand", và skill-matching enrichment của
backend **phụ thuộc 100% vào bảng này**.

---

## Task 4 — Xoá `staging_*` sau khi transform xong

```sql
TRUNCATE staging_jobs, staging_candidates;   -- hoặc DROP nếu chắc không chạy lại
VACUUM FULL;
```

Giải phóng ~167 MB.

---

## Task 5 — Chốt tên cột `jobs`

Schema thống nhất (`backend/database/schema.sql`) ghi `jobs.title`, nhưng bảng
deploy hiện là `jobs.job_title`.

→ Chọn 1: `ALTER TABLE jobs RENAME COLUMN job_title TO title;` **hoặc** sửa
`schema.sql`. Backend tự né được cả hai (`jobs_repo._title_col()`), nhưng nên
thống nhất một tên.

---

## Task 6 — Candidates (chỉ khi team chốt làm feature)

Chỉ làm nếu team quyết làm feature "giỏi hơn X% ứng viên". Cách làm tương tự
Task 2–3 cho `staging_candidates.candidate_skills` → `candidate_skills_mapping`.

Nếu chưa chốt → **bỏ qua**, để dành dung lượng.

---

## Định nghĩa "xong" (backend verify bằng đây)

```sql
SELECT COUNT(*) FROM jobs;                 -- kỳ vọng 20–40k
SELECT COUNT(*) FROM skills;               -- kỳ vọng 5–15k
SELECT COUNT(*) FROM job_skills_mapping;   -- > 0, ~ jobs × 8–15
SELECT pg_size_pretty(pg_database_size(current_database()));  -- < 400 MB

-- sanity: skill phổ biến nhất phải là skill thật, không phải câu văn
SELECT sk.skill_name, COUNT(*) n
FROM job_skills_mapping m
JOIN skills sk ON sk.id = m.skill_id
GROUP BY 1 ORDER BY n DESC LIMIT 15;
```

Dung lượng dự kiến sau cleanup: jobs ~5 MB + skills ~2 MB + companies ~3 MB +
job_skills_mapping ~25 MB + candidates ~5 MB ≈ **~90 MB**. Thoải mái dưới 500.

---

## Nếu vẫn không đủ chỗ

- Nâng Supabase Pro (8 GB, ~$25/mo), hoặc
- Chạy Postgres local + đổi `DATABASE_URL` cho demo.

---

## Backend contract (bảng + cột backend đang đọc)

```
companies(id, name)
skills(id, skill_name)                          -- đã clean + dedup
jobs(id, company_id, title, location, job_level, job_type)
job_skills_mapping(job_id -> jobs.id, skill_id -> skills.id)   PK(job_id, skill_id)
candidates(id, dev_type, degree, years_code_pro, country)
candidate_skills_mapping(candidate_id, skill_id)
```

Chi tiết đầy đủ: `docs/BACKEND_SPEC.md` §5.
