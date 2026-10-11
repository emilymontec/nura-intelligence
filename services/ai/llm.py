import os
import json
import requests
from dotenv import load_dotenv
from .agents import get_agent_options, AGENT_REGISTRY, run_specialist_agent, run_agent_team
from .prompts import EXECUTIVE_REPORT_PROMPT, CHAT_ANALYST_PROMPT, AGENT_ROUTER_PROMPT


load_dotenv()


class LLMRouter:
    def __init__(self):
        self.keys = {
            "groq": os.getenv("GROQ_API_KEY", ""),
            "cerebras": os.getenv("CEREBRAS_API_KEY", ""),
            "openrouter": os.getenv("OPENROUTER_API_KEY", "")
        }
        self.endpoints = {
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "cerebras": "https://api.cerebras.ai/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions"
        }
        self.tiers = {
            "fast": [
                ("groq", "llama-3.1-8b-instant"),
                ("cerebras", "llama3.1-8b"),
                ("openrouter", "google/gemini-2.0-flash-001")
            ],
            "standard": [
                ("groq", "llama-3.3-70b-versatile"),
                ("cerebras", "llama3.1-70b"),
                ("openrouter", "google/gemini-pro-1.5"),
                ("openrouter", "meta-llama/llama-3.3-70b-instruct")
            ],
            "premium": [
                ("openrouter", "anthropic/claude-3.5-sonnet"),
                ("openrouter", "openai/gpt-4o"),
                ("openrouter", "google/gemini-pro-1.5"),
                ("groq", "llama-3.3-70b-versatile")
            ]
        }

    def generate(self, messages: list, tier: str = "standard", temperature: float = 0.4, max_tokens: int = None) -> str:
        sequence = self.tiers.get(tier, self.tiers["standard"])
        if max_tokens is None:
            if tier == "premium":
                max_tokens = 4096
            elif tier == "fast":
                max_tokens = 1024
            else:
                max_tokens = 2048
        for provider, model in sequence:
            api_key = self.keys.get(provider)
            if not api_key:
                continue
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://localhost"
                headers["X-Title"] = "AI Service"
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            try:
                response = requests.post(self.endpoints[provider], headers=headers, json=payload, timeout=45)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[Router] Fallback activado: {provider} ({model}) fallo con estado {response.status_code}.")
            except Exception as e:
                print(f"[Router] Fallback activado: Excepcion con {provider} ({model}) - {str(e)}")
        raise Exception("Todos los proveedores LLM configurados (Groq, Cerebras, OpenRouter) han fallado o no estan configurados.")


router = LLMRouter()


def _run_completion(system_message: str, prompt: str, temperature: float = 0.4, tier: str = "standard") -> str:
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    return router.generate(messages, tier=tier, temperature=temperature)


def generate_ai_report(context_data: dict) -> str:
    prompt = EXECUTIVE_REPORT_PROMPT.format(
        summary=context_data.get('summary', {}),
        health=context_data.get('health', {}),
        trends=context_data.get('trends', {}),
        insights=context_data.get('insights', []),
        industry=context_data.get('industry', 'General / Negocios')
    )
    try:
        return _run_completion(
            system_message="Eres un analista de negocios que habla de forma clara, cercana y sin tecnicismos.",
            prompt=prompt,
            temperature=0.3,
            tier="premium"
        )
    except Exception as e:
        return f"Error al generar el reporte: {str(e)}"


def _summarize_context(context: dict) -> str:
    if not context or not context.get("file_name"):
        return "Actualmente no hay ningún archivo cargado. Estamos en modo de conversación general."
    if context.get("mode") == "rag_document":
        content = context.get("content", "")
        return (
            f"Documento cargado: '{context.get('file_name')}'\n"
            f"Contenido del documento (primera parte):\n{content[:8000]}"
        )
    summary = context.get("summary", {})
    insights = context.get("insights", [])
    industry = context.get("industry", "General / Negocios")
    business_context = context.get("business_context", "")
    critical_vars = context.get("critical_variables", [])
    forecasts = context.get("forecasts", {})
    anomalies = context.get("anomalies", [])
    fraud_signals = context.get("fraud_signals", [])
    columns = context.get("columns", {})
    preview = context.get("preview", [])
    health = context.get("health", {})
    correlations = context.get("correlations", [])
    kpis = context.get("kpis", [])
    lines = [
        f"Información del archivo: Se llama '{context.get('file_name')}' y tiene {summary.get('rows', 0)} filas y {summary.get('columns', 0)} columnas de información.",
        f"Sector del negocio: {industry}",
        f"Descripción del negocio: {business_context}",
        f"Salud de los datos: {health.get('health_score', 0)} de 100 puntos (riesgo {health.get('risk_level', 'desconocido')}).",
    ]
    if columns:
        col_lines = []
        for col_name, col_info in columns.items():
            sem_type = col_info.get('semantic_type', col_info.get('dtype', 'desconocido'))
            missing = col_info.get('missing', 0)
            unique = col_info.get('unique', 0)
            col_lines.append(f"  - {col_name}: {sem_type} (valores faltantes: {missing}, valores únicos: {unique})")
        lines.append("Columnas del dataset:\n" + "\n".join(col_lines))
    if kpis:
        kpi_lines = []
        for kpi in kpis:
            kpi_lines.append(f"  - {kpi['label']}: {kpi['value']}")
        lines.append("KPIs principales:\n" + "\n".join(kpi_lines))
    if preview:
        preview_lines = ["Vista previa de los datos (primeras 8 filas):"]
        col_names = list(preview[0].keys()) if preview else []
        if col_names:
            preview_lines.append("  | " + " | ".join(str(c) for c in col_names) + " |")
            for row in preview[:8]:
                vals = []
                for c in col_names:
                    v = row.get(c)
                    vals.append(str(v) if v is not None else "")
                preview_lines.append("  | " + " | ".join(vals) + " |")
        lines.append("\n".join(preview_lines))
    if correlations:
        corr_lines = ["Relaciones importantes entre variables:"]
        for corr in correlations[:5]:
            corr_lines.append(f"  - {corr['col1']} ↔ {corr['col2']}: {corr['strength']} {corr['direction']} (valor: {corr['correlation']})")
        lines.append("\n".join(corr_lines))
    if anomalies:
        lines.append(f"Valores inusuales detectados: {len(anomalies)} registros que podrían ser errores o casos especiales.")
    if fraud_signals:
        lines.append(f"Alertas de posible fraude o error: {', '.join(fraud_signals[:5])}")
    if critical_vars:
        vars_str = ", ".join([f"{v['column']} (impacto: {v['importance']})" for v in critical_vars[:3]])
        lines.append(f"Variables críticas para el negocio: {vars_str}")
    if forecasts:
        f_lines = ["Tendencias futuras esperadas:"]
        for col, f in forecasts.items():
            growth = f.get('expected_growth', 'desconocido')
            f_lines.append(f"  - {col}: se espera un cambio de {growth}%")
        lines.append("\n".join(f_lines))
    if insights:
        lines.append("Hallazgos clave del análisis:")
        for ins in insights[:6]:
            lines.append(f"  - {ins}")
    return "\n\n".join(lines)


def route_intent(question: str, context: dict, history: str) -> str:
    prompt = AGENT_ROUTER_PROMPT.format(
        question=question,
        history=history,
        agent_options=get_agent_options()
    )
    try:
        response_text = router.generate(
            messages=[
                {"role": "system", "content": "Eres el enrutador de intenciones. Responde ÚNICAMENTE con el key del agente seleccionado."},
                {"role": "user", "content": prompt},
            ],
            tier="fast",
            temperature=0.1,
            max_tokens=15
        )
        selected_key = response_text.strip().lower()
        for char in [".", "'", '"', "`", "\n"]:
            selected_key = selected_key.replace(char, "")
        return selected_key.strip()
    except Exception as e:
        print(f"[Router] Error en route_intent: {e}")
        return "chat"


def chat_with_data(question: str, context: dict, history: str, user_info: dict = None) -> str:
    try:
        short_context = _summarize_context(context)
        if user_info:
            user_block = f"\nUsuario: {user_info.get('name', 'Usuario')} ({user_info.get('email', '')})"
            short_context += user_block
        has_dataset = bool(context and context.get("file_name"))
        industry = context.get("industry", "General / Negocios")
        if not has_dataset or len(question.strip()) < 5:
            selected_key = "chat"
        else:
            selected_key = route_intent(question, short_context, history)

        # El router puede devolver hasta 2 keys separados por coma cuando la
        # pregunta amerita varias perspectivas a la vez (ver
        # AGENT_ROUTER_PROMPT). Antes solo se usaba el primer/único key.
        candidate_keys = [k.strip() for k in selected_key.split(",") if k.strip()]
        selected_agents = []
        for key in candidate_keys[:2]:
            agent = AGENT_REGISTRY.get(key)
            if agent and not (agent.requires_dataset and not has_dataset):
                selected_agents.append(agent)

        if selected_agents:
            def run_specialist_callback(system_message, prompt, temperature=0.25):
                human_system = f"{system_message} Hablas de forma clara, amable y sin tecnicismos."
                return _run_completion(human_system, prompt, temperature, tier="standard")

            def run_synthesis_callback(system_message, prompt, temperature=0.3):
                return _run_completion(system_message, prompt, temperature, tier="standard")

            return run_agent_team(
                selected_agents, question, short_context, history, industry,
                specialist_callback=run_specialist_callback,
                synthesis_callback=run_synthesis_callback,
            )
        prompt = CHAT_ANALYST_PROMPT.format(
            context=short_context,
            history=history,
            question=question,
            industry=industry
        )
        return _run_completion(
            system_message=(
                f"Eres una asistente inteligente que ayuda a entender negocios en el sector de {industry}. "
                "Tu objetivo es que cualquier persona entienda su empresa. Habla siempre de forma sencilla, humana y sin usar jerga técnica."
            ),
            prompt=prompt,
            temperature=0.4,
            tier="standard"
        )
    except Exception as e:
        return f"Error en el sistema de chat (Router falló): {str(e)}"
