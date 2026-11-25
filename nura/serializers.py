from dj_rest_auth.serializers import PasswordResetSerializer
from nura.utils import custom_password_reset_url_generator
from django.conf import settings

class CustomPasswordResetSerializer(PasswordResetSerializer):
    def get_email_options(self):
        return {
            'url_generator': custom_password_reset_url_generator,
            'extra_email_context': {
                'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
            }
        }
