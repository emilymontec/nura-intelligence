"""Módulo 5 — Automatización y Colaboración."""
import datetime
import json
import random

from django.utils import timezone

from .base import AuthenticatedTestCase, csv_file


class TriggerTests(AuthenticatedTestCase):
    def test_scheduled_trigger_without_scheduled_at_is_rejected(self):
        res = self.client.post(
            "/triggers/",
            data=json.dumps({"name": "Mal config", "event_type": "scheduled_date", "action_type": "notify"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 400)

    def test_file_uploaded_trigger_fires_and_logs_on_upload(self):
        res = self.client.post(
            "/triggers/",
            data=json.dumps({"name": "Avisar subida", "event_type": "file_uploaded", "action_type": "notify"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 201)
        trigger_id = res.json()["id"]

        res = self.client.post("/datasets", {"file": csv_file("a,b\n1,2\n", "trig.csv")}, **self.auth)
        self.assertEqual(res.status_code, 201)

        res = self.client.get(f"/triggers/{trigger_id}/", **self.auth)
        detail = res.json()
        self.assertIsNotNone(detail["last_triggered_at"])
        self.assertEqual(len(detail["last_logs"]), 1)

    def test_anomaly_trigger_fires_generate_report(self):
        res = self.client.post(
            "/triggers/",
            data=json.dumps(
                {
                    "name": "Reporte en anomalía",
                    "event_type": "anomaly_detected",
                    "action_type": "generate_report",
                    "config": {"format": "pdf", "audience": "technical"},
                }
            ),
            content_type="application/json",
            **self.auth,
        )
        trigger_id = res.json()["id"]

        random.seed(7)
        rows = [f"{random.uniform(10, 50):.2f},{random.randint(1, 5)}" for _ in range(200)]
        rows.append("5000.00,99")  # outlier obvio para forzar detección de anomalías
        content = "precio,cantidad\n" + "\n".join(rows)
        res = self.client.post("/datasets", {"file": csv_file(content, "anomalia.csv")}, **self.auth)
        self.assertEqual(res.status_code, 201)

        res = self.client.get(f"/triggers/{trigger_id}/", **self.auth)
        detail = res.json()
        self.assertIsNotNone(detail["last_triggered_at"])
        self.assertEqual(detail["last_logs"][0]["status"], "ok")

    def test_scheduled_trigger_fires_via_manual_check(self):
        past = (timezone.now() - datetime.timedelta(minutes=5)).isoformat()
        res = self.client.post(
            "/triggers/",
            data=json.dumps(
                {
                    "name": "Reporte programado",
                    "event_type": "scheduled_date",
                    "action_type": "notify",
                    "config": {"scheduled_at": past},
                }
            ),
            content_type="application/json",
            **self.auth,
        )
        trigger_id = res.json()["id"]

        res = self.client.post("/triggers/check-scheduled/", **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertIn(trigger_id, res.json()["fired_trigger_ids"])


class SharingAndCommentsTests(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.user_b = self.make_user("share_b")
        self.auth_b = self.auth_header(self.user_b)
        self.user_c = self.make_user("share_c")
        self.auth_c = self.auth_header(self.user_c)

        res = self.client.post("/datasets", {"file": csv_file("a,b\n1,2\n", "compartido.csv")}, **self.auth)
        self.dataset_id = res.json()["id"]

    def test_share_by_email_makes_dataset_visible_to_recipient_only(self):
        res = self.client.post(
            "/shares/create/",
            data=json.dumps({"dataset_id": self.dataset_id, "email": "share_b@example.com", "permission": "view"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 201, res.content)

        res = self.client.get("/datasets/shared-with-me/", **self.auth_b)
        shared = res.json()
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["id"], self.dataset_id)

        # No aparece en el propio /datasets de B — sigue siendo de A.
        res = self.client.get("/datasets", **self.auth_b)
        self.assertTrue(all(d["id"] != self.dataset_id for d in res.json()))

        # C, que no recibió el share, no lo ve.
        res = self.client.get("/datasets/shared-with-me/", **self.auth_c)
        self.assertEqual(res.json(), [])

    def test_duplicate_share_is_rejected_with_409(self):
        payload = json.dumps({"dataset_id": self.dataset_id, "email": "share_b@example.com", "permission": "view"})
        res1 = self.client.post("/shares/create/", data=payload, content_type="application/json", **self.auth)
        self.assertEqual(res1.status_code, 201)
        res2 = self.client.post("/shares/create/", data=payload, content_type="application/json", **self.auth)
        self.assertEqual(res2.status_code, 409)

    def test_revoke_share_removes_access(self):
        self.client.post(
            "/shares/create/",
            data=json.dumps({"dataset_id": self.dataset_id, "email": "share_b@example.com", "permission": "view"}),
            content_type="application/json",
            **self.auth,
        )
        shares = self.client.get("/shares/", **self.auth).json()["shared_by_me"]
        share_id = shares[0]["id"]

        res = self.client.delete(f"/shares/{share_id}/", **self.auth)
        self.assertEqual(res.status_code, 204)

        res = self.client.get("/datasets/shared-with-me/", **self.auth_b)
        self.assertEqual(res.json(), [])

    def test_comment_requires_access_shared_user_can_stranger_cannot(self):
        self.client.post(
            "/shares/create/",
            data=json.dumps({"dataset_id": self.dataset_id, "email": "share_b@example.com", "permission": "view"}),
            content_type="application/json",
            **self.auth,
        )

        res = self.client.post(
            "/comments/",
            data=json.dumps({"dataset_id": self.dataset_id, "body": "Buen dataset!"}),
            content_type="application/json",
            **self.auth_b,
        )
        self.assertEqual(res.status_code, 201)

        res = self.client.post(
            "/comments/",
            data=json.dumps({"dataset_id": self.dataset_id, "body": "no debería poder"}),
            content_type="application/json",
            **self.auth_c,
        )
        self.assertEqual(res.status_code, 404)
