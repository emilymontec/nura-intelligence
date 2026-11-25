from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .status_view import api_status
from .health import healthz


def api_404(request, exception=None):
    return JsonResponse(
        {"error": "Ruta no encontrada.", "path": request.path},
        status=404,
    )


def _frontend_url(path):
    return f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')}{path}"


def legacy_verify_email_redirect(request, key):
    return redirect(_frontend_url(f"/verify-email/{key}"))


def legacy_password_reset_redirect(request, uid, token):
    return redirect(_frontend_url(f"/password-reset/confirm/{uid}/{token}"))


handler404 = api_404

urlpatterns = [
    path('', api_status, name='api_status'),
    # Módulo 0 — healthcheck real (JSON, verifica DB + cache) para Docker
    # healthcheck / balanceador de carga / monitoring externo.
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    # Módulo 6 — API pública documentada (antes: drf-spectacular instalado
    # pero sin ningún endpoint de schema/Swagger activado en todo el proyecto).
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', include('chat.urls')),
    # Compatibilidad: los emails antiguos apuntaban a /auth/verify-email/...
    # y /auth/password-reset/confirm/... (rutas del backend, no del frontend).
    # Redirigimos al SPA para que esos enlaces ya enviados no devuelvan 404.
    path('auth/verify-email/<str:key>', legacy_verify_email_redirect, name='legacy_verify_email'),
    path('auth/password-reset/confirm/<str:uid>/<str:token>', legacy_password_reset_redirect, name='legacy_password_reset'),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('accounts/', include('allauth.urls')),
]
