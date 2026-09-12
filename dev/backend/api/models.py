from django.db import models

# The job-market tables (`jobs`, `job_skill`) are owned by Data Engineering and
# created outside Django. They are queried with raw SQL in
# api/repositories/jobs_repo.py — intentionally NO models here, so `makemigrations`
# never tries to create or alter them.
#
# Agreed schema (../../database/schema.sql + ../../database/data_dictionary.md
# — top-level database/ folder, sibling to backend/ and frontend/):
#   companies(id, name)
#   skills(id, skill_name)
#   jobs(id, company_id, job_title, location, job_level, job_type)
#   job_skills_mapping(job_id, skill_id)        -- PK(job_id, skill_id)
#   candidates(id, dev_type, degree, years_code_pro, country)
#   candidate_skills_mapping(candidate_id, skill_id)
