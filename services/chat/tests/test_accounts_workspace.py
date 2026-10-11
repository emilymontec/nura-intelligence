"""Módulo 1 — Cuentas y Workspace."""
import json

from chat.models import Organization, UserProfile, Workspace

from .base import AuthenticatedTestCase, csv_file


class RegistrationAndWorkspaceTests(AuthenticatedTestCase):
    def test_registration_creates_user_profile_and_workspace(self):
        res = self.client.post(
            "/auth/registration/",
            data=json.dumps(
                {
                    "username": "nuevo_usuario",
                    "email": "nuevo@example.com",
                    "password1": "ClavePoderosa123!",
                    "password2": "ClavePoderosa123!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, res.content)

        # El workspace y el UserProfile se crean automáticamente al
        # registrarse (señal post_save en nura/adapters.py), no hace falta
        # un segundo paso manual.
        self.assertTrue(UserProfile.objects.filter(user__username="nuevo_usuario").exists())
        self.assertTrue(Workspace.objects.filter(owner__username="nuevo_usuario").exists())

    def test_login_returns_jwt_access_and_refresh(self):
        self.make_user("login_user")
        res = self.client.post(
            "/auth/login/",
            data=json.dumps({"email": "login_user@example.com", "password": "TestPass123!"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)

    def test_workspace_usage_reflects_plan_limits(self):
        res = self.client.get("/workspace/usage/", **self.auth)
        self.assertEqual(res.status_code, 200)
        usage = res.json()
        self.assertEqual(usage["plan"], "free")
        self.assertEqual(usage["dataset_limit"], 10)
        self.assertEqual(usage["max_file_size_mb"], 20)


class CrossUserIsolationTests(AuthenticatedTestCase):
    """
    El requisito más básico de un sistema multiusuario: un usuario jamás
    debe ver, modificar o poder borrar los datos de otro.
    """

    def setUp(self):
        super().setUp()
        self.other_user = self.make_user("user_b")
        self.other_auth = self.auth_header(self.other_user)

        res = self.client.post(
            "/datasets",
            {"file": csv_file("col_a,col_b\n1,2\n3,4\n", "privado.csv")},
            **self.auth,
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.dataset_id = res.json()["id"]

    def test_user_b_cannot_see_user_a_dataset_in_listing(self):
        res = self.client.get("/datasets", **self.other_auth)
        ids = [d["id"] for d in res.json()]
        self.assertNotIn(self.dataset_id, ids)

    def test_user_b_cannot_fetch_user_a_dataset_detail(self):
        res = self.client.get(f"/datasets/{self.dataset_id}/", **self.other_auth)
        self.assertEqual(res.status_code, 404)

    def test_user_b_cannot_delete_user_a_dataset(self):
        res = self.client.delete(f"/datasets/{self.dataset_id}/", **self.other_auth)
        self.assertEqual(res.status_code, 404)
        # Y sigue existiendo para su dueño real.
        res = self.client.get(f"/datasets/{self.dataset_id}/", **self.auth)
        self.assertEqual(res.status_code, 200)

    def test_unauthenticated_request_is_rejected(self):
        res = self.client.get("/datasets")
        self.assertEqual(res.status_code, 401)


class OrganizationMembershipTests(AuthenticatedTestCase):
    def test_organization_owner_can_invite_member_with_role(self):
        res = self.client.post(
            "/organizations/",
            data=json.dumps({"name": "Mi Empresa"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 201, res.content)
        org_id = res.json()["id"]
        self.assertTrue(Organization.objects.filter(id=org_id, name="Mi Empresa").exists())
