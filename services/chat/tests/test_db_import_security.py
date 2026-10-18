"""
Tests críticos faltantes para `dataset_import_db` (Módulo 2 — importación
desde bases de datos externas). Agregados durante la auditoría del
2026-10-12 junto con la corrección de SSRF en services/chat/db_connector.py.

Antes de esta corrección, un usuario autenticado podía apuntar `host` a
'localhost', '127.0.0.1' o una IP interna/privada y usar el backend de Nura
como proxy de red hacia servicios que no deberían ser alcanzables desde
fuera (SSRF). Estos tests verifican que esa clase de destino quede
bloqueada, y que las protecciones ya existentes contra SQL no-SELECT sigan
funcionando end-to-end a través del endpoint HTTP (antes solo probadas, de
forma indirecta, a nivel de unidad dentro de db_connector.py).
"""
from .base import AuthenticatedTestCase


class DatasetImportDbSecurityTests(AuthenticatedTestCase):
    url = "/datasets/import-db/"

    def _post(self, **overrides):
        body = {
            "dialect": "postgresql",
            "host": "127.0.0.1",
            "port": "5432",
            "database": "internal",
            "username": "u",
            "password": "p",
            "query": "SELECT 1",
        }
        body.update(overrides)
        return self.client.post(self.url, body, **self.auth)

    def test_loopback_host_is_rejected(self):
        res = self._post(host="127.0.0.1")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("error", res.json())

    def test_localhost_hostname_is_rejected(self):
        res = self._post(host="localhost")
        self.assertEqual(res.status_code, 400, res.content)

    def test_private_network_ip_is_rejected(self):
        # Rango RFC1918 típico de una VPC/red interna.
        res = self._post(host="10.0.0.5")
        self.assertEqual(res.status_code, 400, res.content)

    def test_cloud_metadata_ip_is_rejected(self):
        # 169.254.169.254: endpoint de metadata de AWS/GCP/Azure — objetivo
        # clásico de SSRF para robar credenciales del propio servidor.
        res = self._post(host="169.254.169.254")
        self.assertEqual(res.status_code, 400, res.content)

    def test_non_select_query_is_still_rejected_end_to_end(self):
        # No es un host interno, así que debe fallar por la query, no por el host.
        res = self._post(host="example.com", query="DROP TABLE users;")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("error", res.json())

    def test_unauthenticated_request_is_rejected(self):
        res = self.client.post(self.url, {
            "dialect": "postgresql", "host": "example.com", "port": "5432",
            "database": "db", "query": "SELECT 1",
        })
        self.assertEqual(res.status_code, 401)
