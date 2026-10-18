# Auditoría Nura Intelligence — 2026-10-12

Auditoría y corrección directa sobre el proyecto siguiendo las 7 fases pedidas. El código ya venía de rondas de auditoría anteriores (ver comentarios `# FIXED:` previos en el repo) y estaba en buen estado general — los hallazgos de esta ronda son nuevos o no cubiertos antes.

## Resumen del proyecto (Fase 1)

Plataforma de BI conversacional para vendedores de Temu/Shein/AliExpress: Django 6 + DRF (backend), React 19/Vite (frontend), Celery+Redis (async), PostgreSQL/SQLite. Los usuarios suben CSV/XLSX/JSON, un motor de limpieza (`services/analytics/cleaning.py`) perfila y normaliza el dataset, y un sistema multiagente (`services/ai/agents.py`, 7 agentes por área de negocio) responde preguntas en lenguaje natural, detecta anomalías (IsolationForest real de scikit-learn, no reglas fijas), genera pronósticos (regresión lineal explícita, documentada como heurística, no una red neuronal) y exporta reportes PDF/DOCX. Punto de entrada backend: `nura/manage.py` + `nura/urls.py`; frontend: `frontend/src/main.jsx`.

## Hallazgos y correcciones aplicadas

### 🔴 P0 — Críticos (arreglados)

| # | Problema | Archivo | Severidad | Estado |
|---|---|---|---|---|
| 1 | `requirements.txt` guardado en **UTF-16** (pip no puede parsearlo) + `requests` declarado **dos veces** con versiones distintas (2.34.1 y 2.32.3, conflicto de resolución) + `requests==2.32.3` incompatible con `mailjet-rest` (exige ≥2.32.4). Resultado: **`pip install -r requirements.txt` fallaba siempre**, el proyecto no se podía instalar desde cero. | `requirements.txt` | P0 | ✅ Arreglado (re-guardado en UTF-8, versión única `requests==2.32.4`) |
| 2 | `boto3` ausente de `requirements.txt` pese a que `S3Boto3Storage` se activa automáticamente en cuanto hay credenciales de Supabase en `.env` (que las hay, en este mismo proyecto). Cualquier subida de archivo petaba con `ImproperlyConfigured`. Confirmado: **22 de 32 tests fallaban** por esto. | `requirements.txt` | P0 | ✅ Arreglado (`boto3==1.35.74` agregado) |
| 3 | **SSRF** en `POST /datasets/import-db/`: cualquier usuario autenticado podía mandar `host`/`port` arbitrarios (sin restricción de rol) y el backend abría la conexión sin validar el destino — se podía apuntar a `localhost`, a una IP interna de la VPC o al endpoint de metadata de la nube (`169.254.169.254`) y usar el servidor de Nura como proxy de red. La validación de la *query* (solo SELECT) ya existía y era sólida; faltaba validar el *destino*. | `services/chat/db_connector.py:49` (llamado desde `services/chat/views.py:899`) | P0 | ✅ Arreglado: nueva `_assert_host_is_public()` resuelve el host y rechaza loopback/privado/link-local/reservado antes de conectar. Cubierto con 6 tests nuevos. |
| 4 | **Credenciales reales expuestas**: el `.env` incluido en el zip trae API keys reales y funcionales de Groq, OpenRouter, Cerebras, Mailgun y Supabase (incluyendo `DATABASE_URL` con usuario/contraseña de Postgres en texto plano). No es un bug de código — es un hallazgo operacional crítico. | `.env` | P0 | ⚠️ **No se puede "arreglar" en el código — acción manual tuya, ver abajo** |

### 🟠 P1 — Altos (los 3 más importantes, arreglados)

| # | Problema | Archivo | Estado |
|---|---|---|---|
| 1 | `CORS_ALLOW_ALL_ORIGINS=True` + `CORS_ALLOW_CREDENTIALS=True`: combinación que `django-cors-headers` marca explícitamente como insegura — cualquier sitio web podía hacer peticiones autenticadas (con cookies de sesión) al backend desde el navegador de un usuario logueado. | `nura/settings.py` | ✅ Arreglado: ahora usa una allowlist explícita vía `DJANGO_CORS_ALLOWED_ORIGINS` (env), con fallback solo a `localhost:5173` en dev — nunca `*`. |
| 2 | Sin tests de seguridad para `dataset_import_db` (el endpoint más sensible del proyecto — ejecuta queries contra bases de datos externas) ni para los casos límite de `simple_forecast`/`what_if_simulation` (valores negativos, en cero, historial insuficiente). | `services/chat/tests/` | ✅ Arreglado: 8 tests nuevos (ver Fase 5). |
| 3 | `requirements.txt` con `psycopg2` **y** `psycopg2-binary` duplicados (mismo propósito, uno requiere compilar con `libpq-dev` instalado en el sistema). | `requirements.txt` | ✅ Arreglado: se deja solo `psycopg2-binary`. |

### 🟡 P2 — Medios (documentados, no bloqueantes)

- `DJANGO_DEBUG` y `DJANGO_ALLOWED_HOSTS` usan defaults permisivos (`True` / `*`) — intencional para que el proyecto arranque sin configuración en local (mismo patrón que el resto del archivo), pero **hay que fijar `DJANGO_DEBUG=False` y una lista real de hosts en producción**; no se tocó el default porque el flujo de quickstart del README depende de él.
- El pronóstico (`simple_forecast`) es una regresión lineal simple (`np.polyfit`) — está bien documentado en el propio código como heurística explícita, no un modelo entrenado, pero el README/badges mencionan "ML" de forma genérica sin aclarar ese límite al usuario final. Vale la pena una nota visible en la UI de "qué-pasa-si" aclarando que es una proyección lineal, no una predicción de IA entrenada.
- No se encontró SQL injection (no hay `.raw()`/`cursor.execute()` con input dinámico) ni XSS (no hay `dangerouslySetInnerHTML`/`innerHTML` en el frontend) — buena señal, ya cubierto en rondas de auditoría previas.

## Fase 5 — Testing

- **Antes de esta auditoría**: la suite no podía ejecutarse limpia (ver P0 #1 y #2) — con dependencias instaladas, 22/32 tests fallaban por el `boto3` faltante.
- **Después de los arreglos**: `40 passed` (32 existentes + 8 nuevos), 0 fallos.
- **8 tests nuevos agregados**:
  - `services/chat/tests/test_db_import_security.py` (6 tests): host loopback/localhost/red privada/IP de metadata rechazados; query no-SELECT sigue bloqueada end-to-end; endpoint requiere autenticación.
  - `services/chat/tests/test_enterprise.py::ForecastEdgeCaseTests` (2 tests): serie con valores negativos/cero no revienta ni produce `NaN`/`inf`; historial con menos de 3 valores numéricos responde `400` limpio en vez de `500`.

## Cómo correr todo

```bash
cd nura
cp .env.example .env   # y completa tus propias keys — NO reuses las que vinieron en el zip
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python -m pytest -v
```

## ⚠️ Acción tuya — rotación de credenciales (no son parte del código)

El `.env` del zip trae claves reales y funcionales (Groq, OpenRouter, Cerebras, Mailgun, Supabase, y la contraseña de tu base de datos Postgres dentro de `DATABASE_URL`). Como ya viajaron en este chat/subida, trátalas como comprometidas:

1. Rota (regenera) cada una de esas claves en su panel respectivo.
2. Cambia la contraseña del usuario de Postgres en Supabase.
3. No vuelvas a incluir `.env` real en un zip que compartas — solo `.env.example`.
