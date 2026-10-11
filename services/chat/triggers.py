"""
Módulo 5 — motor de ejecución de triggers.

Vive en su propio módulo (no en views.py ni tasks.py) porque lo necesitan
los dos: `views.py` lo llama justo después de crear un dataset (evento
"file_uploaded"), y `tasks.py` lo llama al terminar el análisis asíncrono
(evento "anomaly_detected"), y poner la función en cualquiera de los dos
crearía un import circular.

Las acciones son deliberadamente simples y auto-contenidas:
- "analyze": vuelve a encolar el análisis del dataset (útil para
  trigger de depuración o para forzar re-análisis).
- "notify": no hay un canal de email/push configurado en este proyecto
  (no hay EMAIL_BACKEND ni servicio push), así que "notificar" se
  registra como un TriggerLog — queda visible en `GET /triggers/<id>/` y
  es lo que un canal real (email, Slack) consumiría después. Lo digo
  explícito acá para no fingir un envío que no ocurre.
- "generate_report": genera de verdad un PDF con el motor de reportes del
  Módulo 4 y confirma su tamaño en el log, como prueba de que corrió
  (no lo persiste en disco para no acumular archivos huérfanos).
"""
from django.utils import timezone


def fire_triggers(workspace, event_type, dataset=None):
    """Dispara todos los triggers activos de `workspace` para `event_type`.
    Devuelve la lista de TriggerLog creados (útil para tests)."""
    from .models import Trigger, TriggerLog

    logs = []
    triggers = Trigger.objects.filter(workspace=workspace, event_type=event_type, active=True)
    for trigger in triggers:
        status_, message = _execute_action(trigger, dataset)
        trigger.last_triggered_at = timezone.now()
        trigger.save(update_fields=['last_triggered_at'])
        log = TriggerLog.objects.create(
            trigger=trigger, dataset=dataset, status=status_, message=message,
        )
        logs.append(log)
    return logs


def _execute_action(trigger, dataset):
    try:
        if trigger.action_type == 'analyze':
            if not dataset:
                return 'error', 'No hay dataset asociado a este evento para re-analizar.'
            from .tasks import analyze_dataset_task
            analyze_dataset_task.delay(dataset.id)
            return 'ok', f"Re-análisis encolado para '{dataset.file_name}'."

        if trigger.action_type == 'notify':
            target = dataset.file_name if dataset else trigger.workspace.name
            return 'ok', f"Notificación registrada: '{trigger.name}' sobre '{target}'."

        if trigger.action_type == 'generate_report':
            if not dataset or not dataset.analysis_context:
                return 'error', 'El dataset no tiene un análisis todavía; no se puede generar el reporte.'
            from . import reports
            audience = (trigger.config or {}).get('audience', 'executive')
            fmt = (trigger.config or {}).get('format', 'pdf')
            generator = {
                'pdf': reports.generate_pdf_report,
                'docx': reports.generate_docx_report,
                'pptx': reports.generate_pptx_report,
            }.get(fmt, reports.generate_pdf_report)
            report_bytes = generator(dataset.analysis_context, generated_for=trigger.name, audience=audience)
            return 'ok', f"Reporte {fmt.upper()} ({audience}) generado: {len(report_bytes)} bytes."

        return 'error', f"Tipo de acción desconocido: {trigger.action_type}"
    except Exception as e:
        return 'error', str(e)
