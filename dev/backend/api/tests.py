"""Contract tests — lock the response shapes the frontend depends on.

See docs/BACKEND_SPEC.md §3. Run with:  python manage.py test
"""
from django.test import TestCase


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
        self.assertEqual(set(body["trends"][0]), {"label", "percentage", "direction"})


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
