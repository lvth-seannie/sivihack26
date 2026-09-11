CREATE TABLE IF NOT EXISTS staging_candidates (
    candidate_id INT PRIMARY KEY,
    standardized_role VARCHAR(100) NOT NULL,
    degree VARCHAR(50) NOT NULL,
    years_experience NUMERIC(4, 1) NOT NULL,
    country VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_skills (
    candidate_id INT NOT NULL,
    skill_name VARCHAR(150) NOT NULL,
    PRIMARY KEY (candidate_id, skill_name),
    FOREIGN KEY (candidate_id) REFERENCES staging_candidates (candidate_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS staging_jobs (
    job_id INT PRIMARY KEY,
    job_title TEXT NOT NULL,
    standardized_role VARCHAR(100) NOT NULL,
    company VARCHAR(255) NOT NULL,
    job_location VARCHAR(255) NOT NULL,
    job_level VARCHAR(100) NOT NULL,
    job_type VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id INT NOT NULL,
    skill_name VARCHAR(150) NOT NULL,
    PRIMARY KEY (job_id, skill_name),
    FOREIGN KEY (job_id) REFERENCES staging_jobs (job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_candidates_role ON staging_candidates (standardized_role);
CREATE INDEX IF NOT EXISTS idx_jobs_role ON staging_jobs (standardized_role);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_name ON candidate_skills (skill_name);
CREATE INDEX IF NOT EXISTS idx_job_skills_name ON job_skills (skill_name);