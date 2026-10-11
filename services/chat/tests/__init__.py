"""
Suite de tests automatizados de Nura Intelligence (app `chat`).

Antes de esta iteración, la verificación del proyecto se hacía con una
decena de scripts sueltos (`test_module2.py`, `test_module5.py`, ...) que
cada sesión de trabajo ejecutaba a mano con `python script.py` contra una
base de datos SQLite temporal. Eso probó cada feature en el momento en que
se construyó, pero no quedaba nada que correr automáticamente después — ni
en un commit nuevo, ni en un pipeline de CI, ni para alguien que clona el
repo y quiere confirmar que todo sigue funcionando.

Este paquete reorganiza esa misma cobertura (y la amplía un poco donde
hacía falta) como un suite real de Django `TestCase`, ejecutable con:

    python manage.py test chat          # todos los tests
    python manage.py test chat.tests.test_datasets   # un módulo puntual
    pytest services/chat/tests/          # si se prefiere pytest (ver pytest.ini)

Cada archivo cubre un módulo de la especificación original del proyecto:
  - test_health.py               → Módulo 0 (healthcheck)
  - test_accounts_workspace.py   → Módulo 1 (cuentas, workspace, cuotas, aislamiento)
  - test_datasets.py             → Módulo 2 (carga CSV/XLSX/JSON, chunked upload, merge)
  - test_automation_collaboration.py → Módulo 5 (triggers, compartir, comentarios)
  - test_enterprise.py           → Módulo 6 (agentes por área, qué-pasa-si,
                                     recomendaciones, caché, API pública)
"""
