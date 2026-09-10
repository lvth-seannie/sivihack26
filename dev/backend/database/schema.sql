-- 1. Core Entities
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) UNIQUE NOT NULL
);

-- 2. Main Data Tables
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    company_id INT REFERENCES companies(id),
    title VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    job_level VARCHAR(100),
    job_type VARCHAR(100)
);

CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    dev_type VARCHAR(255),
    degree VARCHAR(255),
    years_code_pro INT,
    country VARCHAR(255)
);

-- 3. Junction (Mapping) Tables for the many-to-many relationships
CREATE TABLE job_skills_mapping (
    job_id INT REFERENCES jobs(id),
    skill_id INT REFERENCES skills(id),
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE candidate_skills_mapping (
    candidate_id INT REFERENCES candidates(id),
    skill_id INT REFERENCES skills(id),
    PRIMARY KEY (candidate_id, skill_id)
);
