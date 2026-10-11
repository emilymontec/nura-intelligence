"""
Módulo 3 — memoria de largo plazo.

Antes de este cambio, la "memoria" del chat era solo un resumen +
últimos mensajes de la SESIÓN ACTUAL. El agente 'context' (Asistente de
Memoria) prometía "buscar en archivos antiguos y otros chats" en su
descripción, pero no tenía ninguna forma real de ver otras sesiones —
era pura decoración de prompt.

Esto implementa búsqueda semántica real (TF-IDF + similitud coseno, sin
depender de una API de embeddings externa/de pago) sobre TODO el
historial de mensajes del usuario, incluyendo otras sesiones y otros
datasets analizados en el pasado.
"""
from typing import List, Dict


def search_relevant_history(user, query: str, exclude_session_id: str = None,
                             top_k: int = 4, min_similarity: float = 0.12) -> List[Dict]:
    from .models import ChatMessage

    query = (query or "").strip()
    if not query or len(query) < 4:
        return []

    qs = ChatMessage.objects.filter(
        session__user=user, role__in=['user', 'assistant']
    ).select_related('session').order_by('-created_at')
    if exclude_session_id:
        qs = qs.exclude(session__session_id=exclude_session_id)
    qs = qs[:500]  # cota razonable de rendimiento

    messages = list(qs)
    if len(messages) < 3:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return []

    corpus = [m.content for m in messages]
    try:
        vectorizer = TfidfVectorizer(max_features=3000)
        tfidf_matrix = vectorizer.fit_transform(corpus + [query])
    except ValueError:
        # vocabulario vacío (mensajes solo con stopwords/símbolos, etc.)
        return []

    query_vector = tfidf_matrix[-1]
    doc_vectors = tfidf_matrix[:-1]
    similarities = cosine_similarity(query_vector, doc_vectors).flatten()

    ranked = sorted(zip(similarities, messages), key=lambda pair: -pair[0])

    results = []
    seen_sessions = set()
    for score, msg in ranked:
        if score < min_similarity:
            break
        results.append({
            "session_id": msg.session.session_id,
            "session_title": msg.session.title,
            "role": msg.role,
            "content": msg.content[:500],
            "similarity": round(float(score), 3),
            "created_at": msg.created_at.isoformat(),
        })
        seen_sessions.add(msg.session.session_id)
        if len(results) >= top_k:
            break

    return results


def format_memory_block(matches: List[Dict]) -> str:
    """Convierte los resultados de search_relevant_history en un bloque de
    texto listo para inyectar en el prompt del chat."""
    if not matches:
        return ""
    lines = ["[Memoria de otras conversaciones — posiblemente relevante]:"]
    for m in matches:
        who = "Usuario" if m["role"] == "user" else "Asistente"
        lines.append(f"- (chat \"{m['session_title']}\") {who}: {m['content']}")
    return "\n".join(lines)
