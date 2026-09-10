"""Read-only access to the Data Engineering job-market tables.

Agreed schema (see backend/database/schema.sql — owned by Data Eng, created
outside Django):

    companies(id, name)
    skills(id, skill_name)
    jobs(id, company_id, title, location, job_level, job_type)
    job_skills_mapping(job_id, skill_id)          -- PK(job_id, skill_id)

Those tables are not managed by Django migrations, so everything here is raw
SQL. Every function degrades to an empty result if the tables are missing or
empty (e.g. the in-memory test DB, or before Data Eng's ETL runs) so the API
never 500s. Each query runs in its own savepoint so a failure on Postgres does
not poison the surrounding transaction.
"""
from __future__ import annotations

from django.db import DatabaseError, connection, transaction


def _rows(sql: str, params: list | None = None) -> list[tuple]:
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(sql, params or [])
                return cur.fetchall()
    except DatabaseError:
        return []


def _title_col() -> str:
    """`schema.sql` settled on `jobs.title`, but the deployed table currently
    has `jobs.job_title`. Resolve whichever exists so the repo keeps working
    across Data Eng's ETL runs. Prefers `title` when both are present."""
    rows = _rows(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs'
          AND column_name IN ('title', 'job_title')
        ORDER BY (column_name = 'title') DESC
        LIMIT 1
        """
    )
    return rows[0][0] if rows else "title"


def total_jobs() -> int:
    rows = _rows("SELECT COUNT(*) FROM jobs")
    return int(rows[0][0]) if rows else 0


def skill_counts() -> list[tuple[str, int]]:
    """(skill_name, number of distinct jobs requiring it)."""
    return _rows(
        """
        SELECT s.skill_name, COUNT(DISTINCT jsm.job_id) AS n
        FROM job_skills_mapping jsm
        JOIN skills s ON s.id = jsm.skill_id
        WHERE s.skill_name IS NOT NULL AND TRIM(s.skill_name) <> ''
        GROUP BY s.skill_name
        """
    )


def title_counts() -> list[tuple[str, int]]:
    """(raw job title, number of postings with that exact title)."""
    col = _title_col()
    return _rows(
        f"""
        SELECT {col} AS title, COUNT(*) AS n
        FROM jobs
        WHERE {col} IS NOT NULL AND TRIM({col}) <> ''
        GROUP BY {col}
        """
    )


def location_counts() -> list[tuple[str, int]]:
    """(raw jobs.location, number of postings)."""
    return _rows(
        """
        SELECT location, COUNT(*) AS n
        FROM jobs
        WHERE location IS NOT NULL AND TRIM(location) <> ''
        GROUP BY location
        """
    )


def level_counts() -> list[tuple[str, int]]:
    """(job_level lowered/trimmed, number of postings)."""
    return _rows(
        """
        SELECT LOWER(TRIM(job_level)) AS lvl, COUNT(*) AS n
        FROM jobs
        WHERE job_level IS NOT NULL AND TRIM(job_level) <> ''
        GROUP BY LOWER(TRIM(job_level))
        """
    )


def type_counts() -> list[tuple[str, int]]:
    """(job_type lowered/trimmed, number of postings) — e.g. onsite/hybrid/remote."""
    return _rows(
        """
        SELECT LOWER(TRIM(job_type)) AS jt, COUNT(*) AS n
        FROM jobs
        WHERE job_type IS NOT NULL AND TRIM(job_type) <> ''
        GROUP BY LOWER(TRIM(job_type))
        """
    )


def job_skill_pairs() -> list[tuple[int, str]]:
    """(job_id, skill_name lowered/trimmed) — one row per (job, skill). Used for
    set-membership stats where GROUP BY in SQL would over- or under-count."""
    return _rows(
        """
        SELECT jsm.job_id, LOWER(TRIM(s.skill_name)) AS skill
        FROM job_skills_mapping jsm
        JOIN skills s ON s.id = jsm.skill_id
        WHERE s.skill_name IS NOT NULL AND TRIM(s.skill_name) <> ''
        """
    )


def skill_counts_for_titles(titles: list[str]) -> list[tuple[str, int]]:
    """(skill_name lowered, distinct jobs) restricted to postings whose title is
    in `titles`. Used for optional role-requirement enrichment."""
    if not titles:
        return []
    col = _title_col()
    placeholders = ", ".join(["%s"] * len(titles))
    return _rows(
        f"""
        SELECT LOWER(TRIM(s.skill_name)) AS skill, COUNT(DISTINCT jsm.job_id) AS n
        FROM job_skills_mapping jsm
        JOIN jobs j ON j.id = jsm.job_id
        JOIN skills s ON s.id = jsm.skill_id
        WHERE j.{col} IN ({placeholders})
          AND s.skill_name IS NOT NULL AND TRIM(s.skill_name) <> ''
        GROUP BY LOWER(TRIM(s.skill_name))
        """,
        list(titles),
    )
