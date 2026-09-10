"""Read-only access to the Data Engineering job-market tables.

Schema (owned by Data Eng, created outside Django):

    jobs(job_id, job_title, company, job_location, job_level, job_type)
    job_skill(job_id, skill)          -- many rows per job, no primary key

Because those tables are not managed by Django migrations, everything here is
raw SQL. Every function degrades to an empty result if the tables are missing
(e.g. the in-memory test DB) so the API never 500s on a cold database. Each
query runs in its own savepoint so a failure on Postgres does not poison the
surrounding transaction.
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


def total_jobs() -> int:
    rows = _rows("SELECT COUNT(*) FROM jobs")
    return int(rows[0][0]) if rows else 0


def skill_counts() -> list[tuple[str, int]]:
    """(skill, number of distinct jobs requiring it). Skill is lower/trimmed."""
    return _rows(
        """
        SELECT LOWER(TRIM(skill)) AS skill, COUNT(DISTINCT job_id) AS n
        FROM job_skill
        WHERE skill IS NOT NULL AND TRIM(skill) <> ''
        GROUP BY LOWER(TRIM(skill))
        """
    )


def title_counts() -> list[tuple[str, int]]:
    """(raw job_title, number of postings with that exact title)."""
    return _rows(
        """
        SELECT job_title, COUNT(*) AS n
        FROM jobs
        WHERE job_title IS NOT NULL AND TRIM(job_title) <> ''
        GROUP BY job_title
        """
    )


def location_counts() -> list[tuple[str, int]]:
    """(raw job_location, number of postings)."""
    return _rows(
        """
        SELECT job_location, COUNT(*) AS n
        FROM jobs
        WHERE job_location IS NOT NULL AND TRIM(job_location) <> ''
        GROUP BY job_location
        """
    )


def skill_counts_for_titles(titles: list[str]) -> list[tuple[str, int]]:
    """(skill, distinct jobs) restricted to postings whose title is in `titles`."""
    if not titles:
        return []
    placeholders = ", ".join(["%s"] * len(titles))
    return _rows(
        f"""
        SELECT LOWER(TRIM(js.skill)) AS skill, COUNT(DISTINCT js.job_id) AS n
        FROM job_skill js
        JOIN jobs j ON j.job_id = js.job_id
        WHERE j.job_title IN ({placeholders})
          AND js.skill IS NOT NULL AND TRIM(js.skill) <> ''
        GROUP BY LOWER(TRIM(js.skill))
        """,
        list(titles),
    )
