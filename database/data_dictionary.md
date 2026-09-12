# Data Dictionary - AI Career Navigation System

## 1. Overview & Architecture
Hệ thống lưu trữ cơ sở dữ liệu trên Supabase (PostgreSQL) phục vụ bài toán khuyến nghị công việc và phân tích khoảng cách kỹ năng (Skill-gap Analysis).
- **Tầng đệm (Staging Layer):** Chứa dữ liệu gốc đã clean sơ bộ từ Kaggle/StackOverflow (`staging_jobs`, `staging_candidates`).
- **Tầng sản xuất (Production Core):** Lược đồ quan hệ chuẩn hóa gồm 6 bảng: `companies`, `skills`, `jobs`, `candidates`, `job_skills_mapping`, `candidate_skills_mapping`.

---

## 2. Standardized Role Taxonomy (5 Nhóm vai trò chuẩn)
Toàn bộ `dev_type` của ứng viên và chức danh của việc làm được quy chuẩn hóa nghiêm ngặt về 5 nhóm chính:
1. **Software Engineer**: Frontend, Backend, Full-stack, Mobile, DevOps, Cloud Engineer.
2. **Data Analyst**: BI Analyst, Data Analytics, Reporting Specialist.
3. **Data Engineer**: ETL Developer, Big Data, Database Administrator.
4. **Business Analyst**: Product Analyst, Systems Analyst, Requirements Engineer.
5. **Product Manager**: Project Manager, Scrum Master, Technical Product Owner.
*(Các vai trò không thuộc nhóm kỹ thuật số trên được phân loại vào `Other`).*

---

## 3. Detailed Table Specifications

### 3.1. `companies`
Bảng danh mục công ty tuyển dụng duy nhất.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT` (SERIAL) | PK, Auto-increment | Mã định danh duy nhất của công ty |
| `name` | `TEXT` | NOT NULL, UNIQUE | Tên công ty (đã trim khoảng trắng) |

### 3.2. `skills`
Từ điển kỹ năng kỹ thuật duy nhất được bóc tách từ cả công việc và ứng viên.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT` (SERIAL) | PK, Auto-increment | Mã định danh duy nhất của kỹ năng |
| `skill_name` | `TEXT` | NOT NULL, UNIQUE | Tên kỹ năng chuẩn (ví dụ: Python, SQL, Docker, AWS) |

### 3.3. `candidates`
Thông tin hồ sơ năng lực của ứng viên.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | PK | Mã định danh ứng viên (tương ứng `candidate_id`) |
| `dev_type` | `TEXT` | NOT NULL | Vai trò nghề nghiệp (đã chuẩn hóa về 5 nhóm chính) |
| `degree` | `TEXT` | NULLABLE | Trình độ học vấn (Bachelor, Master, PhD, Other) |
| `years_code_pro` | `TEXT` | NOT NULL | Số năm kinh nghiệm làm việc thực tế (đã làm sạch NULL) |
| `country` | `TEXT` | NULLABLE | Quốc gia cư trú của ứng viên |

### 3.4. `jobs`
Danh sách các tin tuyển dụng kỹ thuật.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | PK | Mã định danh tin tuyển dụng (tương ứng `job_id`) |
| `company_id` | `INT` | FK -> `companies(id)` | Mã công ty đăng tuyển |
| `job_title` | `TEXT` | NOT NULL | Tiêu đề công việc ban đầu |
| `location` | `TEXT` | NULLABLE | Địa điểm làm việc (thành phố, bang, quốc gia) |
| `job_level` | `TEXT` | NULLABLE | Cấp bậc kinh nghiệm (Associate, Mid senior, Executive) |
| `job_type` | `TEXT` | NULLABLE | Hình thức làm việc (Onsite, Remote, Hybrid, Full-time) |

### 3.5. `candidate_skills_mapping`
Bảng bắc cầu quan hệ Nhiều - Nhiều (N:M) giữa Ứng viên và Kỹ năng (1NF).
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `candidate_id` | `INT` | PK, FK -> `candidates(id)` | Mã ứng viên sở hữu kỹ năng |
| `skill_id` | `INT` | PK, FK -> `skills(id)` | Mã kỹ năng tương ứng |

### 3.6. `job_skills_mapping`
Bảng bắc cầu quan hệ Nhiều - Nhiều (N:M) giữa Công việc và Kỹ năng yêu cầu (1NF).
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `job_id` | `INT` | PK, FK -> `jobs(id)` | Mã công việc yêu cầu kỹ năng |
| `skill_id` | `INT` | PK, FK -> `skills(id)` | Mã kỹ năng tương ứng |