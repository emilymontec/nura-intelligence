"""Módulo 6 — IA Empresarial + Enterprise."""
import json
import random

from .base import AuthenticatedTestCase, csv_file


class AgentsByAreaTests(AuthenticatedTestCase):
    def test_agents_grouped_by_business_area(self):
        res = self.client.get("/agents/by-area/", **self.auth)
        self.assertEqual(res.status_code, 200)
        by_area = res.json()
        for area in ("finanzas", "ventas", "marketing", "operaciones", "general"):
            self.assertIn(area, by_area)
        # Al menos un agente de verdad en finanzas (riesgo/forecast).
        self.assertGreater(len(by_area["finanzas"]), 0)


class WhatIfSimulationTests(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        random.seed(10)
        lines = ["mes,precio,ventas"]
        for i in range(30):
            precio = round(50 - i * 0.3 + random.uniform(-1, 1), 2)
            ventas = round(1000 + i * 20 - precio * 2 + random.uniform(-10, 10), 2)
            lines.append(f"{i},{precio},{ventas}")
        res = self.client.post("/datasets", {"file": csv_file("\n".join(lines), "whatif.csv")}, **self.auth)
        self.dataset_id = res.json()["id"]

    def test_direct_growth_adjustment_and_elasticity_scenarios(self):
        body = {
            "target_col": "ventas",
            "periods": 3,
            "scenarios": [
                {"name": "Crecer 20% más rápido", "growth_adjustment_pct": 20},
                {"name": "Bajar precio 10%", "variable": "precio", "change_pct": -10},
                {"name": "Variable inválida", "variable": "no_existe", "change_pct": 5},
                {"name": "Escenario mal formado"},
            ],
        }
        res = self.client.post(
            f"/datasets/{self.dataset_id}/what-if/",
            data=json.dumps(body),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 200, res.content)
        result = res.json()
        self.assertEqual(result["baseline"]["column"], "ventas")
        self.assertEqual(len(result["scenarios"]), 4)
        self.assertEqual(result["scenarios"][0]["method"], "ajuste_directo_de_crecimiento")
        self.assertEqual(result["scenarios"][1]["method"], "correlacion_como_elasticidad")
        self.assertIn("error", result["scenarios"][2])
        self.assertIn("error", result["scenarios"][3])

    def test_missing_target_col_is_rejected(self):
        res = self.client.post(
            f"/datasets/{self.dataset_id}/what-if/",
            data=json.dumps({"scenarios": [{"growth_adjustment_pct": 1}]}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 400)

    def test_target_col_not_in_dataset_is_rejected(self):
        res = self.client.post(
            f"/datasets/{self.dataset_id}/what-if/",
            data=json.dumps({"target_col": "no_existe", "scenarios": [{"growth_adjustment_pct": 1}]}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 400)


class ProactiveRecommendationsTests(AuthenticatedTestCase):
    def test_recommendations_auto_generate_on_upload_with_nulls_and_outlier(self):
        random.seed(11)
        rows = []
        for i in range(200):
            precio = "" if i % 15 == 0 else f"{random.uniform(10, 50):.2f}"
            cantidad = random.randint(1, 5)
            rows.append(f"{precio},{cantidad}")
        rows.append("9999.00,50")  # outlier
        content = "precio,cantidad\n" + "\n".join(rows)
        res = self.client.post("/datasets", {"file": csv_file(content, "recs.csv")}, **self.auth)
        dataset_id = res.json()["id"]

        res = self.client.get("/recommendations/", **self.auth)
        recs = res.json()
        self.assertGreater(len(recs), 0)

        # Dismiss oculta de la lista por defecto, pero no la borra.
        rec_id = recs[0]["id"]
        res = self.client.post(f"/recommendations/{rec_id}/dismiss/", **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["dismissed"])

        res = self.client.get("/recommendations/", **self.auth)
        self.assertTrue(all(r["id"] != rec_id for r in res.json()))

        # Regeneración manual es idempotente: no duplica.
        res = self.client.post(f"/datasets/{dataset_id}/generate-recommendations/", **self.auth)
        self.assertEqual(res.status_code, 201)
        res = self.client.get("/recommendations/?dismissed=true", **self.auth)
        by_dataset = [r for r in res.json() if r["dataset"] == dataset_id]
        self.assertEqual(len(by_dataset), len(recs))

    def test_recommendations_are_isolated_per_user(self):
        other = self.make_user("recs_other")
        other_auth = self.auth_header(other)
        res = self.client.get("/recommendations/", **other_auth)
        self.assertEqual(res.json(), [])


class CachingAndApiDocsTests(AuthenticatedTestCase):
    def test_dataset_stats_cache_invalidates_on_create_and_delete(self):
        res = self.client.get("/datasets/stats/", **self.auth)
        self.assertEqual(res.json()["total"], 0)

        res = self.client.post("/datasets", {"file": csv_file("a,b\n1,2\n", "cache.csv")}, **self.auth)
        dataset_id = res.json()["id"]

        res = self.client.get("/datasets/stats/", **self.auth)
        self.assertEqual(res.json()["total"], 1, "El caché no se invalidó al crear el dataset")

        res = self.client.delete(f"/datasets/{dataset_id}/", **self.auth)
        self.assertEqual(res.status_code, 204)

        res = self.client.get("/datasets/stats/", **self.auth)
        self.assertEqual(res.json()["total"], 0, "El caché no se invalidó al borrar el dataset")
