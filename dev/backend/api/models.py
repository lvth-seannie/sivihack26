from django.db import models

# The job-market tables (`jobs`, `job_skill`) are owned by Data Engineering and
# created outside Django. They are queried with raw SQL in
# api/repositories/jobs_repo.py — intentionally NO models here, so `makemigrations`
# never tries to create or alter them.
#
# Reference schema:
#   jobs(job_id, job_title, company, job_location, job_level, job_type)
#   job_skill(job_id, skill)
