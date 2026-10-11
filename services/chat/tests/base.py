"""
Utilidades compartidas por los tests: creación de usuarios autenticados sin
pasar por el flujo HTTP completo de registro (eso ya lo prueba
test_accounts_workspace.py por separado) y helpers para construir archivos
en memoria que simulan una subida real.
"""
import io

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthenticatedTestCase(TestCase):
    """Base con un usuario ya creado y su header JWT listo para usar."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("user_a")
        self.auth = self.auth_header(self.user)

    @staticmethod
    def make_user(username, password="TestPass123!"):
        return User.objects.create_user(
            username=username, email=f"{username}@example.com", password=password
        )

    @staticmethod
    def auth_header(user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def csv_file(content: str, name: str = "dataset.csv") -> io.BytesIO:
    f = io.BytesIO(content.encode("utf-8"))
    f.name = name
    return f
