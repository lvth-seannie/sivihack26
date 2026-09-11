# DATA DICTIONARY - SIVIHACK 2026

### 1. Bảng staging_candidates (Ứng viên)
- **candidate_id**: Mã định danh duy nhất (INT, PK).
- **standardized_role**: 5 vị trí chuẩn (Software Engineer, Data Analyst, Data Engineer, Business Analyst, Product Manager, Other).
- **degree**: Trình độ học vấn cao nhất (Bachelor, Master, PhD, Below Bachelor, Other).
- **years_experience**: Số năm kinh nghiệm làm việc (0.5 đến 50.0).
- **country**: Quốc gia làm việc / sinh sống.

### 2. Bảng candidate_skills (Kỹ năng ứng viên - 1 skill/row)
- **candidate_id**: Khóa ngoại tham chiếu tới staging_candidates(candidate_id).
- **skill_name**: Tên công nghệ / kỹ năng sở hữu (Python, SQL, React, Docker...).

### 3. Bảng staging_jobs (Tin tuyển dụng)
- **job_id**: Mã định danh tin tuyển dụng (INT, PK).
- **job_title**: Tiêu đề tin tuyển dụng gốc.
- **standardized_role**: Vai trò công nghệ đã quy về 5 nhóm chuẩn.
- **company**: Tên công ty tuyển dụng.
- **job_location**: Địa điểm làm việc.
- **job_level**: Cấp bậc (Entry, Mid senior, Associate...).
- **job_type**: Hình thức làm việc (Onsite, Remote, Hybrid).

### 4. Bảng job_skills (Kỹ năng công việc yêu cầu - 1 skill/row)
- **job_id**: Khóa ngoại tham chiếu tới staging_jobs(job_id).
- **skill_name**: Tên kỹ năng công việc yêu cầu.