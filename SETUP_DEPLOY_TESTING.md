# Nura Intelligence — Configuración, Despliegue y Pruebas

> Documento único de referencia para: (1) levantar el proyecto en local o en
> Docker, (2) correr la suite de tests automatizada, y (3) probar manualmente
> los 6 módulos de la plataforma con un dataset ejemplar real de 200 pedidos
> de e-commerce (Temu/Shein/AliExpress). Complementa a `roadmap_nura_intelligence.md`
> (qué está hecho y qué no) y a `README.md` (quickstart de 3 líneas).

---

## 1. Configuración

### 1.1 Variables de entorno

Todo vive en un `.env` en la raíz del proyecto. Copia la plantilla y ajusta
lo que necesites — **todo tiene un fallback de desarrollo**, así que el
proyecto arranca con un `.env` vacío o incompleto:

```bash
cp .env.example .env
```

| Variable | Obligatoria | Fallback si falta | Para qué |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | No (sí en prod) | clave insegura hardcodeada | firma de sesiones/JWT |
| `DJANGO_DEBUG` | No | `True` | tracebacks completos, logging verboso |
| `DJANGO_ALLOWED_HOSTS` | No | `*` | hosts permitidos |
| `DATABASE_URL` | No | SQLite local (`db.sqlite3`) | Postgres en prod/Docker |
| `REDIS_URL` | No | Celery en modo "eager" (síncrono) + caché en memoria | async real + caché compartido |
| `GROQ_API_KEY` / `CEREBRAS_API_KEY` / `OPENROUTER_API_KEY` | **Sí, al menos 1** | el chat no responde | motor de IA conversacional (Módulo 3) |
| `SUPABASE_*` | No | almacenamiento en disco local (`media/`) | storage de archivos en prod |
| `MAILGUN_API_KEY` / `MAILGUN_DOMAIN` | No | emails a consola | verificación de cuenta / recuperación de contraseña |
| `DJANGO_LOG_LEVEL` | No | `DEBUG` en dev, `INFO` en prod | nivel de log de la app |
| `SENTRY_DSN` | No | reporte de errores desactivado | monitoring de excepciones (Módulo 0) |
| `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE` | No | `development`/`production`, `0.0` | contexto y muestreo de Sentry |

**La única variable realmente indispensable para probar el Módulo 3 (chat)
es una API key de IA.** Groq y Cerebras tienen capa gratuita — con cualquiera
de las dos alcanza; el router hace fallback en cascada (Groq → Cerebras →
OpenRouter) si configuras más de una.

### 1.2 Instalar dependencias

```bash
python -m venv venv
source venv/bin/activate          # venv\Scripts\activate en Windows
pip install -r requirements.txt
```

> `requirements.txt` está codificado en UTF-16LE (así venía el proyecto
> original) — `pip` lo lee sin problema, no hace falta convertirlo.

Para el frontend:

```bash
cd frontend
pnpm install   # o: npm install
```

---

## 2. Despliegue

### 2.1 Local, sin Docker (desarrollo del día a día)

```bash
# Terminal 1 — backend
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser     # opcional, para entrar a /admin/
python manage.py runserver

# Terminal 2 — frontend
cd frontend && pnpm run dev
```

Abre **http://localhost:5173** (NO `:8000` — ese puerto es solo la API y
devuelve una página de estado informativa, no la aplicación).

Con `DATABASE_URL` y `REDIS_URL` vacíos, todo corre con SQLite y Celery en
modo síncrono — cero dependencias externas, ideal para probar rápido.

### 2.2 Con Docker Compose (réplica cercana a producción)

```bash
cd docker
cp ../.env.example ../.env    # y completa al menos una API key de IA
docker-compose up --build
```

Esto levanta: Postgres, Redis, el backend Django (con worker de Celery
aparte), un gateway Nginx, y el frontend. El gateway queda en
`http://localhost:8000` y rutea `/admin`, `/auth`, `/chat`, `/datasets`,
etc. al backend y todo lo demás al frontend.

El servicio `chat-service` ahora tiene un `healthcheck:` real apuntando a
`/healthz/` (antes no existía ninguno — Docker no tenía forma de saber si
el contenedor estaba realmente sirviendo tráfico, solo si el proceso
seguía vivo). Puedes verlo con:

```bash
docker-compose ps      # columna STATUS debe decir "healthy" tras ~20-30s
```

### 2.3 Notas de producción

- **Base de datos**: define `DATABASE_URL` apuntando a Postgres real (no
  uses SQLite en producción — no soporta escritura concurrente real).
- **Caché**: define `REDIS_URL` — sin esto, el caché es por proceso
  (`LocMemCache`), y con más de un worker cada uno tendría su propia copia
  desincronizada.
- **Logging**: con `DJANGO_DEBUG=False`, el nivel por defecto baja a `INFO`
  automáticamente. Todo se loguea a stdout con timestamp — cualquier
  orquestador de contenedores (Docker, Kubernetes, Render, Railway...) lo
  captura sin configuración extra.
- **Monitoring**: configura `SENTRY_DSN` para que las excepciones no
  capturadas y los logs `ERROR` se reporten automáticamente a Sentry. Sin
  esto, el proyecto sigue funcionando igual — solo no hay reporte externo.
- **Healthcheck**: `GET /healthz/` devuelve `200` + `{"status":"ok",...}`
  si la base de datos y el caché responden, o `503` si alguno falla. Es el
  endpoint correcto para un balanceador de carga o un probe de liveness.
- **Balanceo de carga entre varias instancias del backend**: `docker-compose
  up --scale backend=3` ya reparte contenedores, pero el `nginx.conf`
  actual apunta a un solo `upstream backend { server chat-service:8000; }`
  — para repartir tráfico de verdad entre réplicas hace falta que ese
  `upstream` liste varios servidores (o se resuelva vía DNS del
  orquestador). Esto es explícitamente una decisión de infraestructura que
  queda fuera de este documento — ver `roadmap_nura_intelligence.md`,
  Módulo 6, para el detalle.
- **SSO / Google Drive-Dropbox**: requieren credenciales OAuth reales de
  terceros (Google Cloud Console, Okta, Dropbox App Console) que no vienen
  con el proyecto — ver el roadmap para el paso exacto si se quiere
  retomar.

---

## 3. Pruebas automatizadas

### 3.1 Correr la suite

```bash
# Con Django (no requiere instalar nada extra)
python manage.py test chat --verbosity=2

# O con pytest (más cómodo para correr un archivo/test puntual)
pytest                                              # toda la suite
pytest services/chat/tests/test_datasets.py         # un módulo
pytest -k test_duplicate_share_is_rejected          # un test por nombre
```

32 tests, ~20 segundos, sin dependencias externas (usa SQLite en memoria y
Celery en modo eager automáticamente dentro del test runner).

### 3.2 Qué cubre cada archivo

Están organizados por módulo de la especificación original, en
`services/chat/tests/`:

| Archivo | Módulo | Qué prueba |
|---|---|---|
| `test_health.py` | 0 | `/healthz/` (DB + caché), schema/Swagger de la API pública |
| `test_accounts_workspace.py` | 1 | registro → workspace automático, login JWT, cuotas por plan, **aislamiento entre usuarios** (404 al intentar ver/borrar datasets ajenos, 401 sin token), organizaciones |
| `test_datasets.py` | 2 | subida CSV, deduplicación por hash, conversión JSON (3 formatos), **subida por chunks** (y limpieza del directorio temporal), fusión de datasets |
| `test_automation_collaboration.py` | 5 | triggers (`file_uploaded`, `anomaly_detected`, `scheduled_date`), compartir por email (y aislamiento correcto), compartir duplicado → 409, revocar acceso, comentarios con control de acceso |
| `test_enterprise.py` | 6 | agentes agrupados por área de negocio, simulaciones qué-pasa-si (ambos métodos + casos inválidos), recomendaciones proactivas automáticas + aislamiento, invalidación de caché en stats |

### 3.3 CI/CD

`.github/workflows/ci.yml` corre automáticamente en cada push/PR a `main`:

- **Job `backend`**: Postgres + Redis reales como servicios de GitHub
  Actions (no el fallback SQLite/eager — así el pipeline también valida la
  ruta de producción), migraciones, `python manage.py check`, la suite
  completa de tests, y una verificación real de `/healthz/` levantando el
  servidor.
- **Job `frontend`**: instala dependencias con pnpm y corre `pnpm run
  build`. (El `package.json` del frontend hoy solo define `dev`/`build`/
  `preview` — no hay lint ni tests de frontend configurados todavía; un
  build exitoso es la única verificación automática disponible por ahora.)

Para verlo correr: cualquier push a una rama con PR hacia `main` lo
dispara, o `workflow_dispatch` para correrlo a mano desde la pestaña
"Actions" de GitHub.

---

## 4. Pruebas manuales guiadas (con el dataset ejemplar de 200 pedidos)

### 4.1 Generar el dataset

Ya viene generado (`dataset_ejemplo_200_pedidos.csv`, junto a este
documento), pero si quieres regenerarlo o hacer uno más grande:

```bash
python scripts/generar_dataset_ejemplo.py                       # 200 filas, el de siempre
python scripts/generar_dataset_ejemplo.py --filas 500 --out grande.csv
```

El dataset simula **201 pedidos** (200 + 1 duplicado deliberado) de las
tres plataformas, con 15 columnas: `id_pedido`, `fecha_pedido`,
`plataforma`, `categoria`, `producto`, `precio_unitario`, `cantidad`,
`descuento_pct`, `costo_envio`, `total_pedido`, `metodo_pago`,
`pais_destino`, `dias_entrega`, `calificacion_cliente`, `estado_pedido`.

**No está limpio a propósito** — y eso es lo que lo hace útil para probar:

- ~5% de `calificacion_cliente` y ~4% de `dias_entrega` vienen vacíos
  (nulos reales, no simulados con `NaN` de pandas).
- **2 outliers de precio** (un `precio_unitario` 25× más alto que lo
  normal, como un error de carga típico con un cero de más).
- **1 fila duplicada exacta** (error común de doble-click al exportar).
- `total_pedido` está matemáticamente correlacionado con `precio_unitario`
  y `cantidad` — debería aparecer como correlación fuerte en el análisis.

### 4.2 Guion de prueba paso a paso

Asumiendo el backend en `http://localhost:8000` y el frontend en
`http://localhost:5173` (local, sin Docker). Cada paso tiene el equivalente
en la interfaz (frontend) y en `curl` (para probar la API directo).

#### Paso 1 — Registro y login (Módulo 1)

En el frontend: pantalla de registro → crea una cuenta → inicia sesión.
Verifica que al entrar ya tienes un workspace propio (no hay que crearlo a
mano).

```bash
curl -X POST http://localhost:8000/auth/registration/ \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password1":"ClaveSegura123!","password2":"ClaveSegura123!"}'

curl -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"ClaveSegura123!"}'
# Guarda el "access" token del JSON de respuesta para los siguientes pasos:
export TOKEN="<access_token_de_la_respuesta>"
```

#### Paso 2 — Subir el dataset (Módulo 2)

En el frontend: "Subir archivo" → selecciona `dataset_ejemplo_200_pedidos.csv`.
Deberías ver el dataset aparecer en tu lista con estado "analizado" en unos
segundos (modo eager local) o tras un breve procesamiento en segundo plano
(con Redis/Celery real).

```bash
curl -X POST http://localhost:8000/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@dataset_ejemplo_200_pedidos.csv"
# Guarda el "id" de la respuesta:
export DATASET_ID="<id>"
```

**Qué verificar**: el análisis automático debería reportar **anomalías
detectadas** (busca los 2 outliers de precio — con este dataset salen
~10, porque Isolation Forest también marca combinaciones normales pero
poco frecuentes, no solo los 2 outliers "evidentes"), y entre los
hallazgos una correlación fuerte entre `precio_unitario`/`cantidad` y
`total_pedido`. El *health score* de este dataset en particular se queda
cerca de 100 — la fórmula actual solo penaliza % de celdas vacías y % de
filas duplicadas (`services/analytics/scoring.py`), y con ~0.6% de nulos
sobre 201×15 celdas el impacto es mínimo; no penaliza outliers (esos se
reportan aparte, como anomalías). Si quieres ver el score caer de verdad,
prueba con `--filas 500` y edita el script para subir el porcentaje de
nulos inyectados.

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/datasets/$DATASET_ID/ | python3 -m json.tool
```

#### Paso 3 — Chat conversacional (Módulo 3)

El chat responde con el contexto del **dataset activo en esa sesión**, que
es distinto de simplemente haberlo subido en el Paso 2 — hay que
"activarlo" en una sesión de chat primero (en el frontend esto pasa solo
al abrir un dataset y empezar a chatear; por API es un paso explícito):

```bash
curl -X POST http://localhost:8000/datasets/$DATASET_ID/activate/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"session_id":"demo-session"}'
```

Ahora sí, pregunta en el frontend o por API:

- *"¿Cuál es la plataforma con más pedidos?"*
- *"¿Hay algo raro en los precios?"* (debería mencionar los outliers)
- *"¿Qué me recomiendas para mejorar?"*

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"message\":\"¿Cuál es la plataforma con más pedidos y cuál tiene mejor calificación promedio?\",\"session_id\":\"demo-session\"}"
```

**Qué verificar**: la respuesta debe usar datos reales del CSV (no
genéricos), y si haces una pregunta amplia tipo *"¿cómo va mi negocio?"*
debería activarse la orquestación multi-agente (varias perspectivas
combinadas en una sola respuesta).

#### Paso 4 — Gráficos y dashboard (Módulo 4)

En el frontend: pestaña de visualización del dataset → deberías ver
barras/líneas por plataforma o categoría, el heatmap de correlación (con
`precio_unitario`, `cantidad`, `descuento_pct`, `costo_envio`,
`total_pedido`, `dias_entrega`, `calificacion_cliente` — 7 columnas
numéricas) y un scatter del par más correlacionado.

Genera un dashboard automático con IA:

```bash
curl -X POST http://localhost:8000/dashboards/generate-ai/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"dataset_id\":$DATASET_ID}"
```

Los reportes (`/sessions/<id>/report/...`) se generan a partir del
**contexto analítico guardado en la sesión de chat** — el mismo que
activaste en el Paso 3 con `/datasets/<id>/activate/`. Si ya hiciste ese
paso con `session_id=demo-session`, exporta directamente:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/sessions/demo-session/report/pdf/?audience=executive" \
  -o reporte_ejecutivo.pdf
```

Prueba también `?audience=technical` y `?audience=financial`, y los
formatos `/report/docx/` y `/report/pptx/` — el contenido debería variar
según la audiencia (el financiero filtra a columnas monetarias como
`precio_unitario`, `costo_envio`, `total_pedido`).

#### Paso 5 — Triggers y recomendaciones proactivas (Módulos 5 y 6)

Crea un trigger que genere un reporte automáticamente cuando se detecten
anomalías en un dataset futuro:

```bash
curl -X POST http://localhost:8000/triggers/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Reporte en anomalía","event_type":"anomaly_detected","action_type":"generate_report","config":{"format":"pdf","audience":"technical"}}'
```

Sube un dataset **nuevo** (la deduplicación es por contenido, no por
nombre de archivo — subir el mismo CSV otra vez con otro nombre da 409;
genera uno distinto con otra semilla) y confirma que el trigger se
disparó:

```bash
python scripts/generar_dataset_ejemplo.py --seed 7 --out pedidos_octubre.csv

curl -X POST http://localhost:8000/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@pedidos_octubre.csv"

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/triggers/ | python3 -m json.tool
# last_triggered_at no debería ser null, y last_logs debe traer el tamaño en bytes del PDF generado
```

Revisa las recomendaciones que se generaron solas (sin que nadie
preguntara nada):

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/recommendations/ | python3 -m json.tool
```

#### Paso 6 — Compartir y colaborar (Módulo 5)

Crea un segundo usuario, comparte el dataset con él por email, y confirma
que puede verlo y comentar, pero un tercer usuario sin acceso no puede:

```bash
curl -X POST http://localhost:8000/auth/registration/ -H "Content-Type: application/json" \
  -d '{"username":"colega","email":"colega@example.com","password1":"ClaveSegura123!","password2":"ClaveSegura123!"}'

curl -X POST http://localhost:8000/shares/create/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"dataset_id\":$DATASET_ID,\"email\":\"colega@example.com\",\"permission\":\"view\"}"
```

En el frontend, inicia sesión como `colega@example.com` y verifica que el
dataset aparece en "Compartido conmigo" (no en su propia lista de
datasets) y que puede dejar un comentario.

#### Paso 7 — Simulación "qué pasa si" (Módulo 6)

```bash
curl -X POST http://localhost:8000/datasets/$DATASET_ID/what-if/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "target_col": "total_pedido",
    "periods": 3,
    "scenarios": [
      {"name": "Subir precios 15%", "variable": "precio_unitario", "change_pct": 15},
      {"name": "Duplicar descuentos promedio", "variable": "descuento_pct", "change_pct": 50}
    ]
  }' | python3 -m json.tool
```

Revisa que cada escenario traiga su `method` (ajuste directo o
correlación-como-elasticidad) y la correlación usada — es una heurística
declarada, no una predicción causal real, y el propio JSON lo dice.

#### Paso 8 — Agentes por área, API pública y salud del sistema (Módulo 6 / 0)

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/agents/by-area/ | python3 -m json.tool
curl http://localhost:8000/healthz/
```

Abre `http://localhost:8000/api/docs/` en el navegador — deberías ver la
documentación Swagger interactiva de toda la API, generada automáticamente
(no mantenida a mano).

### 4.3 Qué significa "éxito" en este recorrido

Si llegaste hasta el Paso 8 sin ningún error 500, con:

- al menos 2 anomalías detectadas en el dataset (deberían salir ~10),
- al menos 1 recomendación generada sola,
- el trigger de `anomaly_detected` disparado,
- el segundo usuario viendo el dataset compartido (y un tercero sin verlo),
- reportes PDF/DOCX/PPTX descargando contenido real y distinto por audiencia,
- `/healthz/` devolviendo `200`,

...entonces los 6 módulos están funcionando de punta a punta con datos
reales, no solo con los tests automatizados.
