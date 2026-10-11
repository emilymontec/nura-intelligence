"""
Módulo 0 — healthcheck real para monitoring/orquestación.

Antes de esto no existía ninguna ruta que un balanceador de carga, Docker
Compose (`healthcheck:`) o un servicio externo (UptimeRobot, Kubernetes
liveness/readiness probe, etc.) pudiera llamar para saber si el backend
está realmente operativo — `api_status` (la vista en '/') devuelve una
página HTML decorativa pensada para un humano, no un JSON apto para
máquinas, y no verifica nada (puede devolver 200 aunque la base de datos
esté caída).

`/healthz/` sí verifica dependencias reales:
  - DB: corre `SELECT 1` contra la conexión configurada (Postgres o SQLite)
  - Cache: hace un set/get de una clave de prueba (Redis o LocMemCache)

Devuelve 200 si todo está bien, 503 si algo falla — el código HTTP es lo
que la mayoría de orquestadores (Docker, Kubernetes, nginx upstream con
`max_fails`) usan para decidir si una instancia está lista para recibir
tráfico, sin tener que parsear el body.
"""
import logging

from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse

logger = logging.getLogger("nura")


def healthz(request):
    checks = {}
    healthy = True

    # --- Base de datos ---
    try:
        conn = connections["default"]
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except OperationalError as exc:
        checks["database"] = f"error: {exc}"
        healthy = False
        logger.error("Healthcheck: base de datos no responde (%s)", exc)

    # --- Cache (Redis o LocMemCache, según CACHES en settings) ---
    try:
        probe_key = "nura:healthz:probe"
        cache.set(probe_key, "ok", 5)
        if cache.get(probe_key) != "ok":
            raise RuntimeError("cache.set/get no coincide")
        checks["cache"] = "ok"
    except Exception as exc:  # noqa: BLE001 — cualquier backend de cache puede fallar distinto
        checks["cache"] = f"error: {exc}"
        healthy = False
        logger.error("Healthcheck: cache no responde (%s)", exc)

    status_code = 200 if healthy else 503
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=status_code,
    )
