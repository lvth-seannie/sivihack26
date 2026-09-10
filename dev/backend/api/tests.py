"""Tests — response-shape contracts + skill-matching unit tests.

See docs/BACKEND_SPEC.md §3 / §4.3. Run with:  python manage.py test api

The test DB has no `jobs` / `job_skill` tables, so market-insights exercises
the stub fallback path here.
"""
from django.test import SimpleTestCase, TestCase

from api.data.role_skill_map import classify_title
from api.repositories import jobs_repo
from api.services import market_insights
from api.services.roadmap import build as build_roadmap
from api.services.skill_matching import diff
from api.services.skills import display, normalize


class HealthTests(TestCase):
    def test_health_ok(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})


class MarketInsightsTests(TestCase):
    def test_shape(self):
        r = self.client.get("/api/market-insights")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(
            set(body),
            {"updatedAt", "topSkills", "topRoles", "topLocations", "trends"},
        )
        self.assertEqual(set(body["topSkills"][0]), {"name", "percentage"})
        for stat in body["trends"]:
            self.assertEqual(set(stat), {"label", "percentage", "caption"})


class RolesTests(TestCase):
    def test_shape(self):
        r = self.client.get("/api/roles")
        self.assertEqual(r.status_code, 200)
        role = r.json()["roles"][0]
        self.assertEqual(set(role), {"id", "label", "requiredSkills"})


class AnalyzeTests(TestCase):
    def _post(self, **body):
        return self.client.post(
            "/api/analyze", data=body, content_type="application/json"
        )

    def test_gap_and_score(self):
        r = self._post(targetRole="Data Engineer", currentSkills=["SQL", "Docker"])
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(
            set(body),
            {"matchScore", "strengths", "missingSkills", "roadmap", "recommendation"},
        )
        self.assertEqual(sorted(body["strengths"]), ["Docker", "SQL"])
        self.assertIn("Python", body["missingSkills"])
        self.assertEqual(body["matchScore"], 33)
        self.assertEqual(set(body["roadmap"][0]), {"phase", "skill", "description"})

    def test_skill_matching_is_case_insensitive(self):
        r = self._post(targetRole="Data Engineer", currentSkills=["sql", "PYTHON"])
        self.assertEqual(sorted(r.json()["strengths"]), ["Python", "SQL"])

    def test_unknown_role_is_400(self):
        self.assertEqual(self._post(targetRole="Wizard", currentSkills=["SQL"]).status_code, 400)

    def test_empty_skills_is_422(self):
        self.assertEqual(self._post(targetRole="Data Engineer", currentSkills=[]).status_code, 422)

    def test_aliased_skill_counts_as_a_match(self):
        # "postgres" -> sql, "py" -> python, "reactjs" -> react
        r = self._post(targetRole="Software Engineer", currentSkills=["postgres", "reactjs"])
        strengths = r.json()["strengths"]
        self.assertIn("SQL", strengths)
        self.assertIn("React", strengths)


class NormalizeTests(SimpleTestCase):
    def test_aliases_and_whitespace(self):
        self.assertEqual(normalize("  JavaScript "), "javascript")
        self.assertEqual(normalize("JS"), "javascript")
        self.assertEqual(normalize("PostgreSQL"), "sql")
        self.assertEqual(normalize("node js"), "node.js")
        self.assertEqual(normalize("React.js"), "react")

    def test_display_round_trips_known_and_unknown(self):
        self.assertEqual(display(normalize("js")), "JavaScript")
        self.assertEqual(display(normalize("aws")), "AWS")
        self.assertEqual(display(normalize("kafka")), "Kafka")


class SkillDiffTests(SimpleTestCase):
    def test_diff_is_case_and_alias_insensitive_and_scored(self):
        gap = diff(["Python", "SQL", "Spark"], ["python", "postgres"])
        self.assertEqual(gap.strengths, ["Python", "SQL"])
        self.assertEqual(gap.missing, ["Spark"])
        self.assertEqual(gap.match_score, 67)

    def test_empty_required_scores_zero(self):
        self.assertEqual(diff([], ["Python"]).match_score, 0)


class RoadmapTests(SimpleTestCase):
    def test_one_ordered_step_per_missing_skill(self):
        steps = build_roadmap(["Python", "Spark", "Airflow"])
        self.assertEqual([s["phase"] for s in steps], ["Phase 1", "Phase 2", "Phase 3"])
        self.assertEqual([s["skill"] for s in steps], ["Python", "Spark", "Airflow"])
        self.assertTrue(all(s["description"] for s in steps))


class MarketSnapshotTests(SimpleTestCase):
    """`trends` is computed from the single snapshot: level mix, remote share,
    AI/ML and cloud skill mentions."""

    def setUp(self):
        self._orig = {
            name: getattr(jobs_repo, name)
            for name in ("total_jobs", "skill_counts", "title_counts",
                         "location_counts", "level_counts", "type_counts",
                         "job_skill_pairs")
        }
        market_insights.clear_cache()
        self.addCleanup(self._restore)

    def _restore(self):
        for name, fn in self._orig.items():
            setattr(jobs_repo, name, fn)
        market_insights.clear_cache()

    def test_snapshot_from_fake_dataset(self):
        jobs_repo.total_jobs = lambda: 100
        jobs_repo.skill_counts = lambda: [("Python", 40), ("AWS", 30)]
        jobs_repo.title_counts = lambda: [("Senior Data Engineer", 60), ("Data Analyst", 40)]
        jobs_repo.location_counts = lambda: [("Berlin, Germany", 100)]
        jobs_repo.level_counts = lambda: [("mid senior", 70), ("associate", 25), ("intern", 5)]
        jobs_repo.type_counts = lambda: [("onsite", 82), ("hybrid", 12), ("remote", 6)]
        jobs_repo.job_skill_pairs = lambda: (
            [(i, "pytorch") for i in range(23)]
            + [(i, "aws") for i in range(29)]
        )

        stats = {s["label"]: s["percentage"] for s in market_insights.get_insights(force=True)["trends"]}
        self.assertEqual(stats["Remote or hybrid roles"], 18)  # hybrid + remote
        self.assertEqual(stats["Mid Senior roles"], 70)
        self.assertEqual(stats["Associate roles"], 25)
        self.assertEqual(stats["Roles requiring AI / ML skills"], 23)
        self.assertEqual(stats["Roles requiring cloud skills"], 29)

    def test_falls_back_to_stub_when_empty(self):
        jobs_repo.total_jobs = lambda: 0
        body = market_insights.get_insights(force=True)
        self.assertTrue(body["trends"])
        self.assertEqual(set(body["trends"][0]), {"label", "percentage", "caption"})


class TitleClassifyTests(SimpleTestCase):
    def test_free_text_titles_bucket_into_ui_roles(self):
        self.assertEqual(classify_title("Senior Data Engineer (m/f/d)"), "Data Engineer")
        self.assertEqual(classify_title("Working Student - Data Analytics"), "Data Analyst")
        self.assertEqual(classify_title("Full Stack Developer"), "Software Engineer")
        self.assertEqual(classify_title("Technical Product Owner"), "Product Manager")
        self.assertIsNone(classify_title("Warehouse Operative"))
