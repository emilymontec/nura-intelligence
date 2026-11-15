from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class NuraAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        key = emailconfirmation.key
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        return f"{frontend_url}/verify-email/{key}"

    def send_mail(self, template_prefix, email, context):
        context['frontend_url'] = getattr(
            settings, 'FRONTEND_URL', 'http://localhost:5173'
        ).rstrip('/')
        super().send_mail(template_prefix, email, context)
