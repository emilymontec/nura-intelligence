from dataclasses import dataclass
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .prompts import AGENT_SPECIALIST_PROMPT, AGENT_SYNTHESIS_PROMPT


@dataclass(frozen=True)
class AgentProfile:
    key: str
    name: str
    focus: str
    goal: str
    triggers: tuple[str, ...]
    requires_dataset: bool = False
    priority: int = 50


AGENT_REGISTRY = {
    "context": AgentProfile(
        key="context",
        name="Asistente de Memoria",
        focus="recordar lo que hablamos antes, buscar en archivos antiguos y dar continuidad a la charla",
        goal="asegurar que la conversación fluya y que recuerde detalles de otros chats o archivos pasados",
        triggers=("antes", "anterior", "dijiste", "hablamos", "recuerda", "contexto", "referias", "archivo antiguo", "otro chat", "pasado"),
        requires_dataset=False,
        priority=100,
    ),
    "risk": AgentProfile(
        key="risk",
        name="Detector de Alertas",
        focus="cosas extrañas, datos faltantes y señales de alarma en tu negocio",
        goal="avisarte de posibles problemas antes de que crezcan",
        triggers=("riesgo", "anomalia", "anomal", "error", "inconsistencia", "alerta", "problema"),
        requires_dataset=False,
        priority=92,
    ),
    "insight": AgentProfile(
        key="insight",
        name="Explorador de Oportunidades",
        focus="descubrimientos interesantes y cosas que están funcionando bien",
        goal="encontrar los puntos positivos y curiosos de tu información",
        triggers=("patron", "insight", "hallazgo", "oportunidad", "comportamiento", "tendencia"),
        requires_dataset=False,
        priority=90,
    ),
    "recommendation": AgentProfile(
        key="recommendation",
        name="Consejero Estratégico",
        focus="pasos a seguir, soluciones y consejos para mejorar",
        goal="darte ideas claras de qué hacer con los resultados obtenidos",
        triggers=("recomienda", "acción", "mejora", "optimiza", "solución", "qué hago", "siguiente paso", "estrategia"),
        requires_dataset=False,
        priority=88,
    ),
    "executive": AgentProfile(
        key="executive",
        name="Visión de Negocio",
        focus="el panorama general, el impacto en dinero y tiempo",
        goal="darte el resumen que un dueño de negocio necesita para decidir rápido",
        triggers=("ejecutivo", "negocio", "prioriza", "dirección", "impacto", "ceo", "gerencia", "visión"),
        requires_dataset=False,
        priority=84,
    ),
    "operations": AgentProfile(
        key="operations",
        name="Gestor de Operaciones",
        focus="el día a día, procesos y cómo hacer las cosas más rápido",
        goal="mejorar la eficiencia de tu trabajo diario",
        triggers=("operacion", "proceso", "eficiencia", "flujo", "cuello", "productivity"),
        requires_dataset=False,
        priority=78,
    ),
    "forecast": AgentProfile(
        key="forecast",
        name="Guía del Futuro",
        focus="hacia dónde van las cosas y qué esperar los próximos meses",
        goal="ayudarte a ver el camino que lleva tu negocio según los datos",
        triggers=("proyeccion", "forecast", "escenario", "futuro", "crec", "caer", "tendencia"),
        requires_dataset=True,
        priority=76,
    ),
}


def get_agent_options() -> str:
    # Antes: 'priority' se definía en cada AgentProfile pero nunca se leía en
    # ningún lugar del código; el orden dependía solo del orden de inserción
    # del diccionario. Ahora se ordena explícitamente por prioridad.
    ordered_agents = sorted(AGENT_REGISTRY.values(), key=lambda a: -a.priority)
    options = []
    for agent in ordered_agents:
        options.append(f"- {agent.key}: {agent.name}. Enfoque: {agent.focus}")
    options.append("- chat: Conversación general o preguntas que no requieren un especialista.")
    return "\n".join(options)


def run_specialist_agent(agent: AgentProfile, question: str, context: str, history: str, industry: str, llm_callback) -> str:
    prompt = AGENT_SPECIALIST_PROMPT.format(
        agent_name=agent.name,
        agent_focus=agent.focus,
        agent_goal=agent.goal,
        industry=industry,
        context=context,
        history=history,
        question=question,
    )
    return llm_callback(prompt=prompt, system_message=f"Eres {agent.name} dentro del sistema multiagente.", temperature=0.25)


def run_agent_team(agents: List[AgentProfile], question: str, context: str, history: str, industry: str,
                    specialist_callback, synthesis_callback) -> str:
    """
    Orquestación multiagente real (Módulo 3). Antes de este cambio, el
    sistema decía ser "multiagente" en los prompts pero solo corría UN
    agente especializado por turno. Ahora, cuando el enrutador decide que
    la pregunta amerita varias perspectivas, se ejecutan 2 agentes en
    PARALELO (con hilos, ya que las llamadas al LLM son de red/E-S, no de
    CPU) y sus respuestas se combinan en una sola respuesta coherente.
    """
    if len(agents) == 1:
        return run_specialist_agent(agents[0], question, context, history, industry, specialist_callback)

    responses = {}
    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        future_to_agent = {
            executor.submit(run_specialist_agent, agent, question, context, history, industry, specialist_callback): agent
            for agent in agents
        }
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            try:
                responses[agent.key] = future.result()
            except Exception as e:
                responses[agent.key] = f"[{agent.name} no pudo responder: {e}]"

    # Mantener el orden original (por prioridad) al presentar las respuestas al sintetizador
    ordered_blocks = []
    for agent in agents:
        text = responses.get(agent.key, "")
        if text:
            ordered_blocks.append(f"### {agent.name} ({agent.focus})\n{text}")
    agent_responses_block = "\n\n".join(ordered_blocks)

    synthesis_prompt = AGENT_SYNTHESIS_PROMPT.format(question=question, agent_responses=agent_responses_block)
    try:
        return synthesis_callback(prompt=synthesis_prompt, system_message="Eres el asesor principal que combina el trabajo del equipo en una sola respuesta.", temperature=0.3)
    except Exception:
        # Si la síntesis falla por cualquier razón, no perdemos el trabajo ya hecho:
        # devolvemos las respuestas del equipo concatenadas como fallback.
        return "\n\n".join(ordered_blocks)
