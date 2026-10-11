from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .status_view import api_status


def api_404(request, exception=None):
    return JsonResponse(
        {"error": "Ruta no encontrada.", "path": request.path},
        status=404,
    )


handler404 = api_404

urlpatterns = [
    path('', api_status, name='api_status'),
    path('admin/', admin.site.urls),
    # Módulo 6 — API pública documentada (antes: drf-spectacular instalado
    # pero sin ningún endpoint de schema/Swagger activado en todo el proyecto).
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', include('chat.urls')),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('accounts/', include('allauth.urls')),
]
