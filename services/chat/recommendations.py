"""
Módulo 6 — recomendaciones proactivas automáticas.

Antes de este cambio, el único lugar donde aparecían "insights" o
"hallazgos" era dentro de un reporte o de una respuesta de chat, es decir,
el usuario tenía que pedirlos explícitamente. Esto genera `Recommendation`
reales en base de datos a partir del mismo análisis que ya se calcula al
subir un dataset (insights, anomalías, señales de fraude, correlaciones,
salud de los datos) — sin que el usuario tenga que preguntar nada — para
que puedan listarse en una bandeja propia ("recomendaciones") fuera del
flujo de chat/reportes.

Es intencionalmente determinístico (no otra llamada a un LLM): reformula
lo que el motor analítico ya encontró, en vez de inventar texto nuevo, así
es barato de correr en cada análisis y 100% reproducible en tests.
"""


def generate_recommendations_for_dataset(dataset):
    """
    Regenera las recomendaciones de un dataset a partir de su
    `analysis_context` ya calculado. Idempotente: borra las recomendaciones
    anteriores de este dataset antes de crear las nuevas, así correr esto
    de nuevo (p. ej. tras un re-análisis) no acumula duplicados.
    Devuelve la lista de Recommendation creadas.
    """
    from .models import Recommendation

    context = dataset.analysis_context or {}
    Recommendation.objects.filter(dataset=dataset).delete()

    created = []

    health = context.get('health', {})
    score = health.get('health_score')
    risk = health.get('risk_level')
    if score is not None and score < 60:
        created.append(Recommendation(
            workspace=dataset.workspace, dataset=dataset, category='calidad_datos',
            title=f"Calidad de datos baja en '{dataset.file_name}' ({score}/100)",
            body=(
                f"El dataset tiene una puntuación de salud de {score}/100 (riesgo {risk}). "
                "Revisá valores nulos, duplicados y tipos de columna antes de usarlo para decisiones importantes."
            ),
        ))

    fraud_signals = context.get('fraud_signals') or []
    for signal in fraud_signals[:3]:
        created.append(Recommendation(
            workspace=dataset.workspace, dataset=dataset, category='riesgo',
            title=f"Posible señal de fraude en '{dataset.file_name}'",
            body=signal,
        ))

    anomalies = context.get('anomalies') or []
    if anomalies:
        created.append(Recommendation(
            workspace=dataset.workspace, dataset=dataset, category='riesgo',
            title=f"{len(anomalies)} registros anómalos detectados en '{dataset.file_name}'",
            body=(
                f"Se detectaron {len(anomalies)} filas con comportamiento fuera de lo común. "
                "Vale la pena revisarlas antes de sacar conclusiones agregadas del dataset."
            ),
        ))

    correlations = context.get('correlations') or []
    for c in correlations[:3]:
        if abs(c.get('correlation', 0)) >= 0.7:
            created.append(Recommendation(
                workspace=dataset.workspace, dataset=dataset, category='oportunidad',
                title=f"Relación fuerte entre {c.get('col1')} y {c.get('col2')}",
                body=(
                    f"Estas dos variables tienen una relación {c.get('direction', '').lower()} "
                    f"{c.get('strength', '').lower()} ({c.get('correlation')}). "
                    "Podría valer la pena investigar si una explica a la otra, o usarla para predecir."
                ),
            ))

    insights = context.get('insights') or []
    for insight in insights[:5]:
        created.append(Recommendation(
            workspace=dataset.workspace, dataset=dataset, category='oportunidad',
            title=f"Hallazgo en '{dataset.file_name}'",
            body=insight,
        ))

    if created:
        Recommendation.objects.bulk_create(created)
    return created
