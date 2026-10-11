"""
Módulo 6 — caché de lectura para endpoints que se consultan mucho y
cambian poco dentro de una sesión de uso normal (estadísticas de
datasets, uso del workspace vs. cuota). Usa el framework de caché de
Django, que ya apunta a Redis o a un caché en memoria local según
`CACHES` en settings.py (mismo patrón de fallback que Celery/DB).

TTL corto (20s) en vez de invalidación exhaustiva en cada mutación: hay
muchos endpoints que cambian un dataset (crear, borrar, archivar,
duplicar, fusionar, restaurar versión...) y perseguir cada uno sería
frágil. Se invalida explícitamente en los puntos de escritura más
frecuentes (crear/borrar dataset) para que la demo se sienta al día, y el
TTL corto cubre el resto sin esfuerzo adicional — es un compromiso
explícito, no un olvido.
"""
from django.core.cache import cache

STATS_TTL_SECONDS = 20
USAGE_TTL_SECONDS = 20


def _stats_key(workspace_id):
    return f"nura:dataset_stats:{workspace_id}"


def _usage_key(workspace_id):
    return f"nura:workspace_usage:{workspace_id}"


def get_cached_dataset_stats(workspace_id):
    return cache.get(_stats_key(workspace_id))


def set_cached_dataset_stats(workspace_id, data):
    cache.set(_stats_key(workspace_id), data, STATS_TTL_SECONDS)


def get_cached_workspace_usage(workspace_id):
    return cache.get(_usage_key(workspace_id))


def set_cached_workspace_usage(workspace_id, data):
    cache.set(_usage_key(workspace_id), data, USAGE_TTL_SECONDS)


def invalidate_workspace_caches(workspace_id):
    cache.delete(_stats_key(workspace_id))
    cache.delete(_usage_key(workspace_id))
