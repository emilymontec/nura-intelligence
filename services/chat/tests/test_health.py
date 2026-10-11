"""Módulo 0 — healthcheck."""
from django.test import TestCase


class HealthzTests(TestCase):
    def test_healthz_returns_200_with_db_and_cache_ok(self):
        res = self.client.get("/healthz/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["checks"]["database"], "ok")
        self.assertEqual(body["checks"]["cache"], "ok")

    def test_api_docs_and_schema_are_served(self):
        # drf-spectacular — Módulo 6, API pública documentada.
        res = self.client.get("/api/schema/")
        self.assertEqual(res.status_code, 200)

        res = self.client.get("/api/docs/")
        self.assertEqual(res.status_code, 200)
