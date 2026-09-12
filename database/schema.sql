-- ========================================================
-- AI CAREER NAV - DATABASE SCHEMA (SUPABASE POSTGRESQL)
-- Architecture: 2 Staging Tables + 6 Production Tables (3NF/1NF)
-- ========================================================

-- Enable extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------
-- 1. STAGING TABLES (ETL Ingestion Layer)
-- --------------------------------------------------------
DROP TABLE IF EXISTS staging_jobs CASCADE;
CREATE TABLE staging_jobs (
    job_id INT PRIMARY KEY,
    job_title TEXT NOT NULL,
    standardized_role TEXT,
    company TEXT,
    job_location TEXT,
    job_level TEXT,
    job_type TEXT,
    job_skills TEXT
);

DROP TABLE IF EXISTS staging_candidates CASCADE;
CREATE TABLE staging_candidates (
    candidate_id INT PRIMARY KEY,
    standardized_role TEXT,
    degree TEXT,
    years_of_experience NUMERIC(4, 1),
    country TEXT,
    candidate_skills TEXT
);

-- --------------------------------------------------------
-- 2. PRODUCTION CORE TABLES (Entities)
-- --------------------------------------------------------
-- Companies Catalog
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Skills Catalog (De-duplicated master list)
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE
);

-- Candidates Master Table
CREATE TABLE IF NOT EXISTS candidates (
    id INT PRIMARY KEY,
    dev_type TEXT NOT NULL,
    degree TEXT,
    years_code_pro TEXT,
    country TEXT
);

-- Jobs Master Table
CREATE TABLE IF NOT EXISTS jobs (
    id INT PRIMARY KEY,
    company_id INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    job_title TEXT NOT NULL,
    location TEXT,
    job_level TEXT,
    job_type TEXT
);

-- --------------------------------------------------------
-- 3. JUNCTION / MAPPING TABLES (Normalized 1NF Relationships)
-- --------------------------------------------------------
-- Candidate to Skills Mapping (Many-to-Many)
CREATE TABLE IF NOT EXISTS candidate_skills_mapping (
    candidate_id INT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

-- Job to Required Skills Mapping (Many-to-Many)
CREATE TABLE IF NOT EXISTS job_skills_mapping (
    job_id INT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

-- Indexes for Fast Query Optimization
CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_cand_id ON candidate_skills_mapping(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill_id ON candidate_skills_mapping(skill_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_job_id ON job_skills_mapping(job_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill_id ON job_skills_mapping(skill_id);