"""
Módulo 2 — procesamiento asíncrono de archivos grandes.

Antes de este cambio, el análisis de cada dataset corría síncrono dentro
del propio request HTTP de subida (bloqueando la respuesta hasta terminar
de leer/limpiar/analizar el archivo completo). Ahora se delega a una tarea
Celery. Si no hay Redis configurado (`REDIS_URL` vacío), Celery corre en
modo "eager" — la tarea se ejecuta igual, solo que de forma síncrona en el
mismo proceso, para que el proyecto siga funcionando en local sin
dependencias externas.
"""
from celery import shared_task


@shared_task(bind=True, max_retries=2)
def analyze_dataset_task(self, dataset_id):
    from .models import Dataset
    from .views import get_analytics_context
    from analytics.utils import make_json_safe

    try:
        dataset = Dataset.objects.get(pk=dataset_id)
    except Dataset.DoesNotExist:
        return {"error": "dataset no encontrado", "dataset_id": dataset_id}

    try:
        dataset.file.seek(0)
        context = get_analytics_context(dataset.file, dataset.file_name)
        dataset.analysis_context = make_json_safe(context)
        dataset.status = 'valid'
        dataset.save(update_fields=['analysis_context', 'status'])

        if context.get('anomalies'):
            from . import triggers as triggers_module
            triggers_module.fire_triggers(dataset.workspace, 'anomaly_detected', dataset=dataset)

        from . import recommendations as recommendations_module
        recommendations_module.generate_recommendations_for_dataset(dataset)

        return {"status": "valid", "dataset_id": dataset_id}
    except Exception as e:
        dataset.status = 'invalid'
        errors = list(dataset.validation_errors or [])
        errors.append(f"Error en análisis: {str(e)}")
        dataset.validation_errors = errors
        dataset.save(update_fields=['status', 'validation_errors'])
        return {"status": "invalid", "dataset_id": dataset_id, "error": str(e)}
