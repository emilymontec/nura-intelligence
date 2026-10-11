import hashlib
import uuid
import io
import json
import traceback
import os
import pandas as pd
import chardet
from docx import Document as DocxDocument
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q, Count
from django.db import models, IntegrityError

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    ChatSession, ChatMessage, UserProfile, Workspace, Dataset, FileCategory, DatasetTag, DatasetVersion,
    Organization, Membership, Dashboard, Trigger, TriggerLog, SharedAccess, Comment, Recommendation,
)
from .serializers import (
    UserProfileSerializer, UserSerializer, WorkspaceSerializer, DatasetSerializer, FileCategorySerializer,
    DatasetTagSerializer, DatasetVersionSerializer, OrganizationSerializer, MembershipSerializer, DashboardSerializer,
    TriggerSerializer, TriggerLogSerializer, SharedAccessSerializer, CommentSerializer, RecommendationSerializer,
)
from . import quotas
from . import reports
from .tasks import analyze_dataset_task
from analytics.analyzer import (
    load_csv, prepare_dataframe, dataset_summary, column_info, evaluate_business,
    analyze_numeric_trends, compute_correlations, detect_industry,
    get_business_context, detect_critical_variables, detect_anomalies,
    check_fraud_signals, simple_forecast, what_if_simulation, get_chart_data, get_preview, get_kpis,
    search_records, filter_records, _json_to_dataframe
)
from analytics.utils import make_json_safe
from ai.llm import generate_ai_report, chat_with_data


def read_dataset_dataframe(dataset) -> pd.DataFrame:
    """
    Lee el archivo de un Dataset ya guardado y lo convierte a DataFrame,
    soportando CSV/XLSX/JSON de forma centralizada.

    Antes de este cambio, 5 vistas distintas (merge, explore, statistics,
    search, filter) repetían el mismo patrón `if file_type == 'csv' ...
    elif file_type == 'xlsx' ... else: no soportado`, lo que significaba
    que un dataset JSON válido (ya analizado correctamente al subirlo)
    quedaba inutilizable en todas esas operaciones. Se reusa `load_csv`,
    que ya sabe leer los tres formatos.
    """
    dataset.file.seek(0)
    return load_csv(dataset.file)

User = get_user_model()

# Constants
ALLOWED_FILE_TYPES = ['csv', 'xlsx', 'json']
# Techo absoluto del sistema (independiente del plan). El límite real por
# plan (más restrictivo) se aplica en quotas.check_storage_quota, que corre
# antes de esta validación.
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        Workspace.objects.create(owner=instance, name=f"Espacio de trabajo de {instance.email}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


def test_endpoint(request):
    return JsonResponse({"status": "ok", "message": "La API esta operativa"})


class MemoryManager:
    RECENT_MESSAGE_LIMIT = 8
    RELEVANT_MESSAGE_LIMIT = 3
    SUMMARY_MESSAGE_LIMIT = 10
    MAX_SUMMARY_CHARS = 1500
    MAX_DECISIONS = 5
    MAX_DATASETS = 3
    MAX_CONTEXT_TOTAL_CHARS = 12000

    def _get_session(self, session_id: str, user) -> ChatSession:
        """
        Obtiene o crea la sesión de chat, siempre escopada al usuario
        autenticado. `user` es obligatorio: ya no existen sesiones
        anónimas/globales (esa era la causa de que todos los usuarios
        compartieran la misma conversación por defecto).
        """
        workspace = getattr(user, 'workspace', None)
        session, _ = ChatSession.objects.get_or_create(
            session_id=session_id,
            user=user,
            defaults={'workspace': workspace},
        )
        return session

    def add_message(self, session_id: str, role: str, content: str, user):
        session = self._get_session(session_id, user)
        ChatMessage.objects.create(session=session, role=role, content=content)
        if role == "user" and (not session.title or session.title in ["Nueva sesión", "Nuevo chat"]):
            session.title = content[:40] if len(content) > 40 else content
            session.save(update_fields=["title", "updated_at"])
        if role == "user":
            self._maybe_update_rolling_summary(session)

    def _maybe_update_rolling_summary(self, session):
        msg_count = session.messages.count()
        if msg_count < self.SUMMARY_MESSAGE_LIMIT:
            return
        messages = list(session.messages.order_by('created_at').values_list('role', 'content'))
        recent = messages[-self.SUMMARY_MESSAGE_LIMIT:]
        lines = []
        for role, content in recent:
            prefix = "Usuario" if role == "user" else "Asistente"
            lines.append(f"{prefix}: {content[:300]}")
        batch = "\n".join(lines)
        existing = session.rolling_summary or ""
        if existing:
            session.rolling_summary = existing[-self.MAX_SUMMARY_CHARS // 2:] + "\n---\n" + batch
        else:
            session.rolling_summary = batch
        session.rolling_summary = session.rolling_summary[-self.MAX_SUMMARY_CHARS:]
        session.save(update_fields=["rolling_summary"])

    def store_dataset_context(self, session_id: str, context: dict, user):
        session = self._get_session(session_id, user)
        session.dataset_context = context or {}
        dataset_history = list(session.dataset_history or [])
        file_name = context.get("file_name", "dataset")
        snapshot = {
            "file_name": file_name,
            "rows": context.get("summary", {}).get("rows", 0),
            "columns": context.get("summary", {}).get("columns", 0),
        }
        if not dataset_history or dataset_history[-1] != snapshot:
            dataset_history.append(snapshot)
        session.dataset_history = dataset_history[-self.MAX_DATASETS:]
        session.save(update_fields=["dataset_context", "dataset_history", "updated_at"])

    def get_dataset_context(self, session_id: str, user) -> dict:
        session = self._get_session(session_id, user)
        return session.dataset_context or {}

    def get_history(self, session_id: str, user, question: str = "") -> str:
        session = self._get_session(session_id, user)
        rolling = session.rolling_summary or ""
        messages = list(session.messages.all()[:20])
        history_parts = []
        for msg in messages:
            history_parts.append(f"{msg.role.upper()}: {msg.content}")
        raw = "\n".join(history_parts)

        parts = []
        if rolling:
            parts.append(f"[Resumen de conversación previa]:\n{rolling}")

        # Memoria de largo plazo (Módulo 3): busca en TODAS las demás
        # sesiones del usuario mensajes semánticamente relacionados con la
        # pregunta actual. Antes, el agente 'context' prometía "recordar
        # otros chats" pero no tenía ninguna forma real de verlos.
        if question:
            from .memory_search import search_relevant_history, format_memory_block
            matches = search_relevant_history(user, question, exclude_session_id=session_id)
            memory_block = format_memory_block(matches)
            if memory_block:
                parts.append(memory_block)

        parts.append(f"[Últimos mensajes]:\n{raw}")
        return "\n\n".join(parts)


memory = MemoryManager()


def validate_file(file_obj):
    """Validar archivo: tamaño, formato, integridad, codificación, estructura"""
    errors = []
    
    # 1. Validar tamaño
    if file_obj.size > MAX_FILE_SIZE:
        errors.append(f"El archivo excede el tamaño máximo permitido de {MAX_FILE_SIZE / (1024*1024)} MB")
    
    # 2. Validar formato
    filename = file_obj.name.lower()
    file_type = None
    if filename.endswith('.csv'):
        file_type = 'csv'
    elif filename.endswith('.xlsx'):
        file_type = 'xlsx'
    elif filename.endswith('.json'):
        file_type = 'json'
    else:
        errors.append(f"Formato de archivo no permitido. Usa: {', '.join(ALLOWED_FILE_TYPES)}")
    
    if errors:
        return False, errors, file_type
    
    # 3. Validar integridad y estructura
    try:
        file_obj.seek(0)
        if file_type == 'csv':
            # Detectar codificación
            raw_data = file_obj.read(10000)
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
            file_obj.seek(0)
            
            # Cargar CSV para validar estructura
            df = pd.read_csv(file_obj, encoding=encoding, nrows=100)
            if df.empty:
                errors.append("El archivo CSV está vacío")
            if len(df.columns) == 0:
                errors.append("El archivo CSV no tiene columnas")
                
        elif file_type == 'xlsx':
            df = pd.read_excel(file_obj, nrows=100)
            if df.empty:
                errors.append("El archivo Excel está vacío")
            if len(df.columns) == 0:
                errors.append("El archivo Excel no tiene columnas")
                
        elif file_type == 'json':
            file_obj.seek(0)
            data = json.load(file_obj)
            if not data:
                errors.append("El archivo JSON está vacío")
                
    except pd.errors.EmptyDataError:
        errors.append("El archivo está vacío")
    except pd.errors.ParserError:
        errors.append("Error al parsear el archivo. Verifica la estructura")
    except json.JSONDecodeError:
        errors.append("Error al parsear el JSON. Verifica la sintaxis")
    except Exception as e:
        errors.append(f"Error de integridad: {str(e)}")
    
    return len(errors) == 0, errors, file_type


def get_analytics_context(file_obj, filename):
    df = load_csv(file_obj)
    df, cleaning_info = prepare_dataframe(df)
    summary = dataset_summary(df)
    cols = column_info(df)
    health = evaluate_business(summary)
    trends = analyze_numeric_trends(df)
    correlations = compute_correlations(df)
    industry = detect_industry(df)
    business_context = get_business_context(df, industry)
    critical_variables = detect_critical_variables(df)
    anomalies = detect_anomalies(df)
    fraud_signals = check_fraud_signals(df)
    numeric_cols = df.select_dtypes(include=['number']).columns
    forecasts = {}
    for col in numeric_cols[:2]:
        try:
            f = simple_forecast(df, col)
            if f:
                forecasts[col] = f
        except Exception as e:
            pass
    charts = get_chart_data(df)
    preview = get_preview(df)
    kpis = get_kpis(df)
    return {
        "file_name": filename,
        "cleaning": cleaning_info,
        "summary": summary,
        "columns": cols,
        "health": health,
        "trends": trends,
        "correlations": correlations,
        "charts": charts,
        "preview": preview,
        "kpis": kpis,
        "industry": industry,
        "business_context": business_context,
        "critical_variables": critical_variables,
        "anomalies": anomalies,
        "fraud_signals": fraud_signals,
        "forecasts": forecasts
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_endpoint(request):
    if 'file' not in request.FILES:
        return Response({"error": "No se ha subido ningún archivo"}, status=status.HTTP_400_BAD_REQUEST)
    file = request.FILES['file']
    session_id = request.POST.get('session_id', 'default')
    user = request.user

    try:
        quotas.check_message_quota(user)
    except quotas.QuotaExceeded as e:
        return Response({"error": e.message, "code": e.code}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    session = memory._get_session(session_id, user)
    session.messages.all().delete()
    memory.add_message(session_id, "user", f"Archivo cargado: {file.name}", user)
    try:
        suffix = file.name.lower().split('.')[-1]
        if suffix not in ['csv', 'xlsx', 'xls', 'json', 'pdf', 'docx', 'doc']:
            return Response({"status": "rag_only", "file_name": file.name, "response": "Archivo cargado."})
        if suffix == 'docx':
            # Antes: los .docx solo se guardaban sin extraer contenido, y el
            # modo "rag_document" de ai/llm.py (que resume un documento para
            # poder chatear sobre él) nunca llegaba a activarse porque nadie
            # generaba ese contexto. Ahora sí se extrae el texto y se guarda.
            try:
                file.seek(0)
                document = DocxDocument(file)
                full_text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
                if not full_text.strip():
                    raise ValueError("El documento no contiene texto extraíble (¿está escaneado o vacío?).")
                rag_context = {"file_name": file.name, "mode": "rag_document", "content": full_text}
                memory.store_dataset_context(session_id, rag_context, user)
                response_text = (
                    f"Leí el documento '{file.name}' ({len(full_text)} caracteres de texto). "
                    "Ya puedes hacerme preguntas sobre su contenido."
                )
                memory.add_message(session_id, "assistant", response_text, user)
                quotas.increment_message_usage(user)
                return Response({"status": "rag_ready", "file_name": file.name, "response": response_text})
            except Exception as e:
                response_text = (
                    f"El archivo '{file.name}' se guardó, pero no pude leer su contenido "
                    f"({str(e)}), así que no podré responder preguntas sobre él."
                )
                memory.add_message(session_id, "assistant", response_text, user)
                return Response({"status": "rag_only", "file_name": file.name, "response": response_text})
        if suffix == 'pdf':
            # Módulo 3 — antes: los .pdf no se leían por falta de una
            # librería de extracción de texto. Ahora se usa pdfplumber.
            try:
                import pdfplumber
                file.seek(0)
                pages_text = []
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages[:50]:  # límite razonable de páginas
                        text = page.extract_text() or ""
                        if text.strip():
                            pages_text.append(text)
                full_text = "\n\n".join(pages_text)
                if not full_text.strip():
                    raise ValueError("El PDF no contiene texto extraíble (¿está escaneado como imagen?).")
                rag_context = {"file_name": file.name, "mode": "rag_document", "content": full_text}
                memory.store_dataset_context(session_id, rag_context, user)
                response_text = (
                    f"Leí el PDF '{file.name}' ({len(pages_text)} páginas con texto, {len(full_text)} caracteres). "
                    "Ya puedes hacerme preguntas sobre su contenido."
                )
                memory.add_message(session_id, "assistant", response_text, user)
                quotas.increment_message_usage(user)
                return Response({"status": "rag_ready", "file_name": file.name, "response": response_text})
            except Exception as e:
                response_text = (
                    f"El archivo '{file.name}' se guardó, pero no pude leer su contenido "
                    f"({str(e)}), así que no podré responder preguntas sobre él."
                )
                memory.add_message(session_id, "assistant", response_text, user)
                return Response({"status": "rag_only", "file_name": file.name, "response": response_text})
        if suffix == 'doc':
            # El formato .doc binario legado (pre-2007) no tiene una
            # librería de extracción liviana equivalente a python-docx; se
            # informa honestamente en vez de fingir que sí se analizó.
            response_text = f"El archivo '{file.name}' fue cargado correctamente. El análisis detallado está disponible para CSV, Excel, Word (.docx) y PDF. El formato .doc antiguo por ahora solo se almacena."
            memory.add_message(session_id, "assistant", response_text, user)
            return Response({"status": "rag_only", "file_name": file.name, "response": response_text})
        file.seek(0)
        context = get_analytics_context(file, file.name)
        safe_context = make_json_safe(context)
        memory.store_dataset_context(session_id, safe_context, user)
        ai_report = generate_ai_report(safe_context)
        score = safe_context.get('health', {}).get('health_score', 0)
        message_parts = [
            f"¡Listo! Ya terminé de revisar tu archivo '{safe_context['file_name']}'.\n\nHe detectado que tu negocio pertenece al sector de {safe_context.get('industry', 'General / Negocios')}.\nAnalicé un total de {safe_context.get('summary', {}).get('rows', 0)} filas de información.\nEn cuanto a la salud de tus datos, les doy una puntuación de {score:.0f} sobre 100 (un nivel de riesgo {safe_context.get('health', {}).get('risk_level', 'desconocido').lower()})."
        ]
        if ai_report:
            message_parts.append(f"\n\n📝 Resumen Ejecutivo para ti:\n{ai_report}")
        full_response = "\n".join(message_parts)
        memory.add_message(session_id, "assistant", full_response, user)
        quotas.increment_message_usage(user)
        safe_context["response"] = full_response
        return Response(safe_context)
    except Exception as e:
        err = f"Error al analizar el archivo: {str(e)}"
        print(f"[ERROR] CRASH EN ANALISIS: {err}")
        traceback.print_exc()
        return Response({"error": err, "exception": type(e).__name__, "detail": repr(e), "response": err}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_endpoint(request):
    try:
        data = request.data
        message = (data.get("message", "") or "").strip()
        session_id = data.get("session_id", "default")
        user = request.user
        if not message:
            return Response({"error": "El mensaje no puede estar vacío."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quotas.check_message_quota(user)
        except quotas.QuotaExceeded as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        memory.add_message(session_id, "user", message, user)
        history = memory.get_history(session_id, user, message)
        context = memory.get_dataset_context(session_id, user)
        user_info = {
            "name": getattr(user, 'first_name', '') or user.email.split('@')[0],
            "email": user.email,
        }
        response_text = chat_with_data(message, context, history, user_info=user_info)
        memory.add_message(session_id, "assistant", response_text, user)
        quotas.increment_message_usage(user)
        return Response({"response": response_text})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    # Antes: devolvía TODAS las sesiones de TODOS los usuarios sin filtrar.
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
    session_data = [
        {
            "session_id": s.session_id,
            "title": s.title,
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]
    return Response({"sessions": session_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_history(request, session_id):
    session, _ = ChatSession.objects.get_or_create(
        session_id=session_id, user=request.user,
        defaults={'workspace': getattr(request.user, 'workspace', None)},
    )
    messages = session.messages.filter(role__in=['user', 'assistant']).order_by('created_at')
    message_data = [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
    return Response({
        "session_id": session.session_id,
        "title": session.title,
        "dataset_context": session.dataset_context,
        "messages": message_data,
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def rename_session(request, session_id):
    try:
        new_title = (request.data.get("title", "") or "").strip()
        if not new_title:
            return Response({"error": "El título no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST)
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
        session.title = new_title
        session.save(update_fields=["title", "updated_at"])
        return Response({"status": "ok", "title": session.title})
    except ChatSession.DoesNotExist:
        return Response({"error": "Sesión no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
        session.delete()
        return Response({"status": "ok", "message": "Sesión eliminada correctamente"})
    except ChatSession.DoesNotExist:
        return Response({"error": "Sesión no encontrada"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    elif request.method == 'PUT':
        data = request.data
        user_data = data.pop('user', None)
        
        profile_serializer = UserProfileSerializer(profile, data=data, partial=True)
        if profile_serializer.is_valid():
            profile_serializer.save()
            
            if user_data:
                user_serializer = UserSerializer(request.user, data=user_data, partial=True)
                if user_serializer.is_valid():
                    user_serializer.save()
            
            return Response(UserProfileSerializer(profile).data)
        return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_workspace(request):
    workspace, created = Workspace.objects.get_or_create(owner=request.user, defaults={'name': f"Espacio de trabajo de {request.user.email}"})
    if request.method == 'GET':
        serializer = WorkspaceSerializer(workspace)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = WorkspaceSerializer(workspace, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_session_report_pdf(request, session_id):
    """
    Módulo 4: genera y descarga un PDF ejecutivo con el análisis del
    dataset activo en la sesión indicada. Antes de este cambio no existía
    ningún endpoint de exportación real: el botón del frontend era solo
    texto decorativo.
    """
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return Response({"error": "Sesión no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    audience = request.query_params.get('audience', 'executive')
    try:
        user_name = getattr(request.user, 'first_name', '') or request.user.email
        pdf_bytes = reports.generate_pdf_report(session.dataset_context, generated_for=user_name, audience=audience)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"No se pudo generar el PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    file_name = session.dataset_context.get("file_name", "dataset")
    safe_name = "".join(c for c in file_name.rsplit(".", 1)[0] if c.isalnum() or c in (" ", "-", "_")).strip() or "reporte"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="reporte_{safe_name}.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_session_report_docx(request, session_id):
    """Igual que export_session_report_pdf pero en formato Word editable."""
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return Response({"error": "Sesión no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    audience = request.query_params.get('audience', 'executive')
    try:
        user_name = getattr(request.user, 'first_name', '') or request.user.email
        docx_bytes = reports.generate_docx_report(session.dataset_context, generated_for=user_name, audience=audience)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"No se pudo generar el DOCX: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    file_name = session.dataset_context.get("file_name", "dataset")
    safe_name = "".join(c for c in file_name.rsplit(".", 1)[0] if c.isalnum() or c in (" ", "-", "_")).strip() or "reporte"
    response = HttpResponse(
        docx_bytes,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="reporte_{safe_name}.docx"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_session_report_pptx(request, session_id):
    """Igual que export_session_report_pdf pero como diapositivas PowerPoint."""
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return Response({"error": "Sesión no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    audience = request.query_params.get('audience', 'executive')
    try:
        user_name = getattr(request.user, 'first_name', '') or request.user.email
        pptx_bytes = reports.generate_pptx_report(session.dataset_context, generated_for=user_name, audience=audience)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"No se pudo generar el PPTX: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    file_name = session.dataset_context.get("file_name", "dataset")
    safe_name = "".join(c for c in file_name.rsplit(".", 1)[0] if c.isalnum() or c in (" ", "-", "_")).strip() or "reporte"
    response = HttpResponse(
        pptx_bytes,
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    response["Content-Disposition"] = f'attachment; filename="reporte_{safe_name}.pptx"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workspace_usage(request):
    """Uso actual vs límites del plan: almacenamiento, datasets y mensajes/día."""
    from . import caching

    workspace, _ = Workspace.objects.get_or_create(
        owner=request.user, defaults={'name': f"Espacio de trabajo de {request.user.email}"}
    )
    cached = caching.get_cached_workspace_usage(workspace.id)
    if cached is not None:
        return Response(cached)

    data = quotas.workspace_usage_summary(workspace)
    caching.set_cached_workspace_usage(workspace.id, data)
    return Response(data)


# Dataset Endpoints

def create_dataset_from_django_file(user, workspace, django_file):
    """
    Lógica compartida para crear un Dataset a partir de un archivo Django
    ya en memoria/disco (InMemoryUploadedFile, TemporaryUploadedFile o
    ContentFile). La usan la subida normal, el import por URL, el import
    por base de datos externa, y el ensamblado de archivos grandes por
    chunks — para no duplicar validación/cuotas/hash/análisis en 4 lugares.
    Devuelve una Response lista para retornar desde la vista.
    """
    try:
        quotas.check_storage_quota(workspace, django_file.size)
        quotas.check_dataset_count_quota(workspace)
    except quotas.QuotaExceeded as e:
        return Response({"error": e.message, "code": e.code}, status=status.HTTP_402_PAYMENT_REQUIRED)

    is_valid, errors, file_type = validate_file(django_file)
    django_file.seek(0)

    file_hash = Dataset.compute_file_hash_static(django_file)
    django_file.seek(0)

    existing = Dataset.objects.filter(file_hash=file_hash, workspace=workspace).first()
    if existing:
        return Response(
            {"error": "Ya existe un archivo idéntico en tu workspace", "existing": DatasetSerializer(existing).data},
            status=status.HTTP_409_CONFLICT
        )

    dataset = Dataset(
        file=django_file,
        original_name=django_file.name,
        file_name=django_file.name,
        file_size=django_file.size,
        file_type=file_type or 'unknown',
        uploaded_by=user,
        workspace=workspace,
        status='valid' if is_valid else 'invalid',
        validation_errors=errors,
    )
    try:
        dataset.save()
    except IntegrityError:
        return Response({"error": "Ya existe un archivo idéntico en tu workspace"}, status=status.HTTP_409_CONFLICT)

    from . import triggers as triggers_module, caching as caching_module
    triggers_module.fire_triggers(workspace, 'file_uploaded', dataset=dataset)
    caching_module.invalidate_workspace_caches(workspace.id)

    if is_valid and file_type in ['csv', 'xlsx', 'json']:
        dataset.status = 'processing'
        dataset.save(update_fields=['status'])
        analyze_dataset_task.delay(dataset.id)
        dataset.refresh_from_db()

    return Response(DatasetSerializer(dataset).data, status=status.HTTP_201_CREATED)


def _build_safe_headers(raw_headers):
    """Valida y limpia el dict de headers que manda el usuario para una
    integración REST/GraphQL de terceros (Módulo 5). Cap de cantidad y
    tamaño para no habilitar abuso, nada más — el usuario es dueño de la
    API externa a la que apunta, así que el header en sí (p. ej. un token
    Bearer) es su responsabilidad."""
    if not raw_headers:
        return {}, None
    if not isinstance(raw_headers, dict):
        return None, "'headers' debe ser un objeto {nombre: valor}"
    if len(raw_headers) > 10:
        return None, "Máximo 10 headers por integración"
    cleaned = {}
    for k, v in raw_headers.items():
        key, val = str(k)[:100], str(v)[:1000]
        if "\n" in key or "\r" in key or "\n" in val or "\r" in val:
            return None, "Los headers no pueden contener saltos de línea"
        cleaned[key] = val
    return cleaned, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_import_url(request):
    """
    Módulo 2/5 — carga de datos desde fuentes externas (APIs REST).
    Descarga un JSON desde una URL y lo convierte en un dataset, igual que
    si se hubiera subido un archivo .json manualmente. Reutiliza el mismo
    parser tolerante (_json_to_dataframe) construido para el soporte JSON.
    Soporta headers propios (p. ej. 'Authorization: Bearer ...') y método
    GET/POST con body JSON, para integrarse con APIs REST de terceros que
    requieren autenticación — no solo endpoints públicos.
    """
    import requests as req_lib
    from django.core.files.base import ContentFile

    url = (request.data.get('url') or '').strip()
    name = (request.data.get('name') or '').strip()
    method = (request.data.get('method') or 'GET').strip().upper()
    body = request.data.get('body')
    if not url:
        return Response({"error": "Se requiere una URL"}, status=status.HTTP_400_BAD_REQUEST)
    if not (url.startswith('http://') or url.startswith('https://')):
        return Response({"error": "La URL debe empezar con http:// o https://"}, status=status.HTTP_400_BAD_REQUEST)
    if method not in ('GET', 'POST'):
        return Response({"error": "method debe ser GET o POST"}, status=status.HTTP_400_BAD_REQUEST)

    extra_headers, err = _build_safe_headers(request.data.get('headers'))
    if err:
        return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    headers = {"User-Agent": "Nura-Intelligence/1.0", **extra_headers}
    try:
        if method == 'POST':
            resp = req_lib.post(url, json=body if isinstance(body, dict) else None, timeout=15, headers=headers)
        else:
            resp = req_lib.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
    except req_lib.RequestException as e:
        return Response({"error": f"No se pudo descargar la URL: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        raw = resp.json()
        data_path = (request.data.get('data_path') or '').strip()
        if data_path:
            for key in data_path.split('.'):
                raw = raw[key] if isinstance(raw, dict) else raw[int(key)]
        df = _json_to_dataframe(raw)
    except Exception as e:
        return Response({"error": f"La URL no devolvió un JSON tabular válido: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    file_name = f"{name or 'import_url'}.csv"
    django_file = ContentFile(csv_bytes, name=file_name)
    django_file.size = len(csv_bytes)

    response = create_dataset_from_django_file(request.user, workspace, django_file)
    if response.status_code == status.HTTP_201_CREATED:
        Dataset.objects.filter(pk=response.data['id']).update(source_url=url)
        response.data['source_url'] = url
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_import_graphql(request):
    """
    Módulo 5 — carga de datos desde una API **GraphQL** de terceros.
    Manda {query, variables} por POST al endpoint indicado, toma la
    respuesta bajo `data` (o el sub-camino que indique `data_path`, p. ej.
    "data.users") y la convierte en dataset con el mismo parser tolerante
    de JSON. Las APIs GraphQL casi siempre requieren autenticación, por eso
    acepta los mismos `headers` configurables que la integración REST.
    """
    import requests as req_lib
    from django.core.files.base import ContentFile

    url = (request.data.get('url') or '').strip()
    query = (request.data.get('query') or '').strip()
    variables = request.data.get('variables') or {}
    name = (request.data.get('name') or '').strip()
    data_path = (request.data.get('data_path') or '').strip()

    if not url or not query:
        return Response({"error": "Se requieren 'url' y 'query'"}, status=status.HTTP_400_BAD_REQUEST)
    if not (url.startswith('http://') or url.startswith('https://')):
        return Response({"error": "La URL debe empezar con http:// o https://"}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(variables, dict):
        return Response({"error": "'variables' debe ser un objeto"}, status=status.HTTP_400_BAD_REQUEST)

    extra_headers, err = _build_safe_headers(request.data.get('headers'))
    if err:
        return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    headers = {"User-Agent": "Nura-Intelligence/1.0", "Content-Type": "application/json", **extra_headers}

    try:
        resp = req_lib.post(url, json={"query": query, "variables": variables}, timeout=15, headers=headers)
        resp.raise_for_status()
    except req_lib.RequestException as e:
        return Response({"error": f"No se pudo consultar la API GraphQL: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = resp.json()
    except Exception as e:
        return Response({"error": f"La respuesta no es JSON válido: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    if payload.get('errors'):
        return Response({"error": f"La API GraphQL devolvió errores: {payload['errors']}"}, status=status.HTTP_400_BAD_REQUEST)

    raw = payload.get('data', payload)
    try:
        if data_path:
            for key in data_path.split('.'):
                raw = raw[key] if isinstance(raw, dict) else raw[int(key)]
        df = _json_to_dataframe(raw)
    except Exception as e:
        return Response({"error": f"No se pudo convertir la respuesta en una tabla: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    file_name = f"{name or 'import_graphql'}.csv"
    django_file = ContentFile(csv_bytes, name=file_name)
    django_file.size = len(csv_bytes)

    response = create_dataset_from_django_file(request.user, workspace, django_file)
    if response.status_code == status.HTTP_201_CREATED:
        Dataset.objects.filter(pk=response.data['id']).update(source_url=url)
        response.data['source_url'] = url
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_import_db(request):
    """
    Módulo 2 — carga de datos desde bases de datos externas.
    Las credenciales viajan solo en este request (nunca se guardan), se
    usan para una única consulta SELECT validada, y se descartan. Ver
    services/chat/db_connector.py para el detalle de las validaciones de
    seguridad (solo lectura, sin sentencias apiladas, sin comentarios).
    """
    from .db_connector import build_safe_connection_url, run_read_only_query, UnsafeQueryError
    from django.core.files.base import ContentFile

    dialect = (request.data.get('dialect') or '').strip()
    host = (request.data.get('host') or '').strip()
    port = (request.data.get('port') or '').strip()
    database = (request.data.get('database') or '').strip()
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    query = request.data.get('query') or ''
    name = (request.data.get('name') or '').strip()

    if not all([dialect, host, port, database, query]):
        return Response(
            {"error": "Se requieren: dialect, host, port, database y query."},
            status=status.HTTP_400_BAD_REQUEST
        )

    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    try:
        connection_url = build_safe_connection_url(dialect, host, port, database, username, password)
        df = run_read_only_query(connection_url, query)
    except UnsafeQueryError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"No se pudo conectar o consultar la base de datos: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    if df.empty or len(df.columns) == 0:
        return Response({"error": "La consulta no devolvió datos."}, status=status.HTTP_400_BAD_REQUEST)

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    file_name = f"{name or 'import_db'}.csv"
    django_file = ContentFile(csv_bytes, name=file_name)
    django_file.size = len(csv_bytes)
    return create_dataset_from_django_file(request.user, workspace, django_file)


CHUNK_UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'chunk_uploads')
MAX_CHUNKS = 2000  # ~2000 chunks * 5MB = 10GB tope absoluto


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_upload_chunk(request):
    """
    Módulo 2 — subida en partes (chunked upload) para archivos grandes.
    El cliente parte el archivo en pedazos (p. ej. 5 MB cada uno), genera
    un `upload_id` único por archivo, y va mandando cada pedazo con su
    `chunk_index` y `total_chunks`. Esta vista los va guardando en disco
    por separado; cuando llega el último, los ensambla en orden y crea el
    Dataset con la misma lógica que una subida normal (cuotas, hash,
    análisis asíncrono).
    """
    import re as re_module

    upload_id = (request.data.get('upload_id') or '').strip()
    file_name = (request.data.get('file_name') or '').strip()
    chunk_index = request.data.get('chunk_index')
    total_chunks = request.data.get('total_chunks')
    chunk = request.FILES.get('chunk')

    if not upload_id or not file_name or chunk is None:
        return Response({"error": "Se requieren upload_id, file_name y chunk"}, status=status.HTTP_400_BAD_REQUEST)
    if not re_module.match(r'^[a-zA-Z0-9_-]{8,100}$', upload_id):
        return Response({"error": "upload_id inválido"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)
    except (TypeError, ValueError):
        return Response({"error": "chunk_index y total_chunks deben ser enteros"}, status=status.HTTP_400_BAD_REQUEST)
    if total_chunks <= 0 or total_chunks > MAX_CHUNKS or not (0 <= chunk_index < total_chunks):
        return Response({"error": "chunk_index/total_chunks fuera de rango"}, status=status.HTTP_400_BAD_REQUEST)

    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    upload_dir = os.path.join(CHUNK_UPLOAD_DIR, str(request.user.id), upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    chunk_path = os.path.join(upload_dir, f"{chunk_index}.part")
    with open(chunk_path, 'wb') as f:
        for block in chunk.chunks():
            f.write(block)

    received = len([f for f in os.listdir(upload_dir) if f.endswith('.part')])
    if received < total_chunks:
        return Response({"status": "chunk_received", "received": received, "total": total_chunks})

    try:
        from django.core.files.base import ContentFile
        assembled = io.BytesIO()
        for i in range(total_chunks):
            part_path = os.path.join(upload_dir, f"{i}.part")
            if not os.path.exists(part_path):
                return Response({"error": f"Falta el pedazo {i} de {total_chunks}"}, status=status.HTTP_400_BAD_REQUEST)
            with open(part_path, 'rb') as pf:
                assembled.write(pf.read())
        assembled.seek(0)
        size = assembled.getbuffer().nbytes
        django_file = ContentFile(assembled.read(), name=file_name)
        django_file.size = size
        return create_dataset_from_django_file(request.user, workspace, django_file)
    finally:
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dataset_list_create(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    
    if request.method == 'GET':
        search = request.query_params.get('search', '')
        file_type = request.query_params.get('type', '')
        status_filter = request.query_params.get('status', '')
        category_id = request.query_params.get('category', '')
        starred = request.query_params.get('starred', '')
        sort = request.query_params.get('sort', '-uploaded_at')
        
        datasets = Dataset.objects.filter(workspace=workspace)
        
        archived = request.query_params.get('archived', '')
        if archived == 'true':
            datasets = datasets.filter(archived=True)
        else:
            datasets = datasets.filter(archived=False)
        
        if search:
            datasets = datasets.filter(
                Q(file_name__icontains=search) | 
                Q(original_name__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        if file_type:
            datasets = datasets.filter(file_type=file_type)
        if status_filter:
            datasets = datasets.filter(status=status_filter)
        if category_id:
            datasets = datasets.filter(category_id=category_id)
        if starred == 'true':
            datasets = datasets.filter(starred=True)

        allowed_sorts = ['uploaded_at', '-uploaded_at', 'file_name', '-file_name', 'file_size', '-file_size']
        if sort in allowed_sorts:
            datasets = datasets.order_by(sort)
        
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        if 'file' not in request.FILES:
            return Response({"error": "No se ha subido ningún archivo"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']

        # Cuotas del plan: tamaño máximo, almacenamiento total y cantidad de datasets
        try:
            quotas.check_storage_quota(workspace, file.size)
            quotas.check_dataset_count_quota(workspace)
        except quotas.QuotaExceeded as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_402_PAYMENT_REQUIRED)

        # Validar archivo
        is_valid, errors, file_type = validate_file(file)
        file.seek(0)
        
        # Crear dataset
        file_hash = Dataset.compute_file_hash_static(file)
        file.seek(0)

        existing = Dataset.objects.filter(file_hash=file_hash, workspace=workspace).first()
        if existing:
            serializer = DatasetSerializer(existing)
            return Response(
                {"error": "Ya existe un archivo idéntico en tu workspace", "existing": serializer.data},
                status=status.HTTP_409_CONFLICT
            )

        dataset = Dataset(
            file=file,
            original_name=file.name,
            file_name=file.name,
            file_size=file.size,
            file_type=file_type or 'unknown',
            uploaded_by=request.user,
            workspace=workspace,
            status='valid' if is_valid else 'invalid',
            validation_errors=errors
        )
        try:
            dataset.save()
        except IntegrityError:
            serializer = DatasetSerializer(existing) if existing else None
            return Response(
                {"error": "Ya existe un archivo idéntico en tu workspace"},
                status=status.HTTP_409_CONFLICT
            )
        except Exception as e:
            traceback.print_exc()
            return Response(
                {"error": f"Error al guardar el archivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        from . import triggers as triggers_module, caching as caching_module
        triggers_module.fire_triggers(workspace, 'file_uploaded', dataset=dataset)
        caching_module.invalidate_workspace_caches(workspace.id)

        # Análisis asíncrono vía Celery (Módulo 2). Antes: el análisis
        # corría síncrono aquí mismo, bloqueando la respuesta HTTP hasta
        # terminar de leer/limpiar/analizar el archivo completo. Sin Redis
        # configurado, Celery corre en modo eager (síncrono en el mismo
        # proceso) — por eso se refresca `dataset` desde la BD después de
        # encolar, para que la respuesta ya incluya el resultado en local.
        if is_valid and file_type in ['csv', 'xlsx', 'json']:
            dataset.status = 'processing'
            dataset.save(update_fields=['status'])
            analyze_dataset_task.delay(dataset.id)
            dataset.refresh_from_db()

        serializer = DatasetSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def dataset_detail(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = DatasetSerializer(dataset)
        return Response(serializer.data)
    
    elif request.method in ('PUT', 'PATCH'):
        if 'file_name' in request.data:
            dataset.file_name = request.data['file_name']
        if 'description' in request.data:
            dataset.description = request.data['description']
        if 'tags' in request.data:
            dataset.tags = request.data['tags']
        if 'starred' in request.data:
            dataset.starred = request.data['starred']
        if 'category' in request.data:
            cat_id = request.data['category']
            if cat_id:
                try:
                    dataset.category = FileCategory.objects.get(pk=cat_id, workspace=workspace)
                except FileCategory.DoesNotExist:
                    return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)
            else:
                dataset.category = None
        dataset.save()
        serializer = DatasetSerializer(dataset)
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        if dataset.file:
            dataset.file.delete(save=False)
        dataset.delete()
        from . import caching as caching_module
        caching_module.invalidate_workspace_caches(workspace.id)
        return Response({"status": "ok", "message": "Dataset eliminado correctamente"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_activate(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    
    session_id = request.data.get('session_id', 'default')
    session, _ = ChatSession.objects.get_or_create(session_id=session_id, user=request.user, workspace=workspace)
    
    session.dataset = dataset
    session.dataset_context = dataset.analysis_context
    session.save()
    
    return Response({"status": "ok", "message": "Dataset activado correctamente"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_rename(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    new_name = request.data.get('file_name', '').strip()
    if not new_name:
        return Response({"error": "El nombre no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST)

    dataset.file_name = new_name
    dataset.save(update_fields=['file_name', 'updated_at'])
    return Response(DatasetSerializer(dataset).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_bulk_delete(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    ids = request.data.get('ids', [])
    if not ids:
        return Response({"error": "No se proporcionaron IDs"}, status=status.HTTP_400_BAD_REQUEST)

    datasets = Dataset.objects.filter(pk__in=ids, workspace=workspace)
    count = datasets.count()
    for ds in datasets:
        if ds.file:
            ds.file.delete(save=False)
    datasets.delete()
    from . import caching as caching_module
    caching_module.invalidate_workspace_caches(workspace.id)
    return Response({"status": "ok", "deleted": count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_move(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    category_id = request.data.get('category_id')
    if category_id:
        try:
            category = FileCategory.objects.get(pk=category_id, workspace=workspace)
            dataset.category = category
        except FileCategory.DoesNotExist:
            return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    else:
        dataset.category = None

    dataset.save(update_fields=['category', 'updated_at'])
    return Response(DatasetSerializer(dataset).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_toggle_star(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    dataset.starred = not dataset.starred
    dataset.save(update_fields=['starred', 'updated_at'])
    return Response({"starred": dataset.starred})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_stats(request):
    from . import caching

    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    cached = caching.get_cached_dataset_stats(workspace.id)
    if cached is not None:
        return Response(cached)

    datasets = Dataset.objects.filter(workspace=workspace)

    total = datasets.count()
    by_type = {}
    for ds in datasets.values('file_type').annotate(count=models.Count('id')):
        by_type[ds['file_type']] = ds['count']

    by_status = {}
    for ds in datasets.values('status').annotate(count=models.Count('id')):
        by_status[ds['status']] = ds['count']

    total_size = sum(ds.file_size for ds in datasets)
    starred = datasets.filter(starred=True).count()

    data = {
        "total": total,
        "by_type": by_type,
        "by_status": by_status,
        "total_size": total_size,
        "starred": starred,
    }
    caching.set_cached_dataset_stats(workspace.id, data)
    return Response(data)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def category_list_create(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    if request.method == 'GET':
        categories = FileCategory.objects.filter(workspace=workspace)
        serializer = FileCategorySerializer(categories, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        name = request.data.get('name', '').strip()
        color = request.data.get('color', '#6366f1')
        if not name:
            return Response({"error": "El nombre es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        cat, created = FileCategory.objects.get_or_create(
            name=name, workspace=workspace, defaults={'color': color}
        )
        return Response(FileCategorySerializer(cat).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def category_detail(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        cat = FileCategory.objects.get(pk=pk, workspace=workspace)
    except FileCategory.DoesNotExist:
        return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    Dataset.objects.filter(category=cat).update(category=None)
    cat.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_duplicate(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    dataset.file.seek(0)
    new_name = request.data.get('file_name', f"Copia de {dataset.file_name}")
    new_ds = Dataset(
        file=dataset.file,
        original_name=dataset.original_name,
        file_name=new_name,
        file_size=dataset.file_size,
        file_type=dataset.file_type,
        file_hash=f"{dataset.file_hash}_{uuid.uuid4().hex[:8]}",
        uploaded_by=request.user,
        workspace=workspace,
        status=dataset.status,
        validation_errors=list(dataset.validation_errors),
        analysis_context=dict(dataset.analysis_context),
        description=dataset.description,
        tags=list(dataset.tags),
        category=dataset.category,
        starred=False,
    )
    new_ds.save()
    serializer = DatasetSerializer(new_ds)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_archive(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    dataset.archived = not dataset.archived
    dataset.archived_at = timezone.now() if dataset.archived else None
    dataset.save(update_fields=['archived', 'archived_at', 'updated_at'])
    return Response({"archived": dataset.archived, "archived_at": dataset.archived_at})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_reanalyze(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if dataset.file_type not in ['csv', 'xlsx']:
        return Response({"error": "Solo se pueden analizar archivos CSV y Excel"}, status=status.HTTP_400_BAD_REQUEST)

    dataset.status = 'processing'
    dataset.save(update_fields=['status'])

    try:
        dataset.file.seek(0)
        context = get_analytics_context(dataset.file, dataset.file_name)
        dataset.analysis_context = make_json_safe(context)
        dataset.status = 'valid'
        dataset.save(update_fields=['analysis_context', 'status', 'updated_at'])
    except Exception as e:
        dataset.status = 'invalid'
        dataset.validation_errors.append(f"Error en re-análisis: {str(e)}")
        dataset.save(update_fields=['status', 'validation_errors', 'updated_at'])
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(DatasetSerializer(dataset).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_download(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    from django.http import FileResponse
    try:
        dataset.file.seek(0)
        response = FileResponse(dataset.file.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{dataset.file_name}"'
        return response
    except Exception:
        return Response({"error": "No se pudo descargar el archivo"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_merge(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    ids = request.data.get('dataset_ids', [])
    merge_type = request.data.get('type', 'concat')
    new_name = request.data.get('file_name', 'Dataset fusionado')
    join_column = request.data.get('join_column', '')

    if len(ids) < 2:
        return Response({"error": "Se necesitan al menos 2 datasets para fusionar"}, status=status.HTTP_400_BAD_REQUEST)

    datasets = Dataset.objects.filter(pk__in=ids, workspace=workspace)
    if datasets.count() != len(ids):
        return Response({"error": "Algunos datasets no fueron encontrados"}, status=status.HTTP_404_NOT_FOUND)

    try:
        frames = []
        for ds in datasets:
            try:
                df = read_dataset_dataframe(ds)
            except Exception:
                continue
            frames.append(df)

        if not frames:
            return Response({"error": "No se pudieron leer los archivos"}, status=status.HTTP_400_BAD_REQUEST)

        if merge_type == 'concat':
            merged = pd.concat(frames, ignore_index=True)
        elif merge_type == 'join' and join_column:
            merged = frames[0]
            for f in frames[1:]:
                if join_column in merged.columns and join_column in f.columns:
                    merged = merged.merge(f, on=join_column, how='left', suffixes=('', '_dup'))
                else:
                    merged = pd.concat([merged, f], ignore_index=True)
        else:
            merged = pd.concat(frames, ignore_index=True)

        import io as _io
        buffer = _io.BytesIO()
        merged.to_csv(buffer, index=False)
        buffer.seek(0)

        from django.core.files.base import ContentFile
        file_content = ContentFile(buffer.read(), name=f"{new_name}.csv")
        file_hash = hashlib.sha256(buffer.getvalue()).hexdigest()
        buffer.seek(0)
        file_size = len(buffer.getvalue())

        ds = Dataset(
            file=file_content,
            original_name=f"{new_name}.csv",
            file_name=f"{new_name}.csv",
            file_size=file_size,
            file_type='csv',
            file_hash=f"{file_hash}_{uuid.uuid4().hex[:8]}",
            uploaded_by=request.user,
            workspace=workspace,
            status='valid',
            description=f"Fusionado de {datasets.count()} datasets: {', '.join(ds.file_name for ds in datasets)}",
        )
        ds.save()

        ds.file.seek(0)
        context = get_analytics_context(ds.file, ds.file_name)
        ds.analysis_context = make_json_safe(context)
        ds.save(update_fields=['analysis_context'])

        return Response(DatasetSerializer(ds).data, status=status.HTTP_201_CREATED)
    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"Error al fusionar: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def tag_list_create(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    if request.method == 'GET':
        tag_filter = request.query_params.get('tag', '')
        tags = DatasetTag.objects.filter(workspace=workspace)
        if tag_filter:
            tags = tags.filter(name__icontains=tag_filter)
        serializer = DatasetTagSerializer(tags, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        name = request.data.get('name', '').strip()
        color = request.data.get('color', '#6366f1')
        if not name:
            return Response({"error": "El nombre es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        tag, created = DatasetTag.objects.get_or_create(
            name=name, workspace=workspace, defaults={'color': color}
        )
        return Response(DatasetTagSerializer(tag).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def tag_detail(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        tag = DatasetTag.objects.get(pk=pk, workspace=workspace)
    except DatasetTag.DoesNotExist:
        return Response({"error": "Etiqueta no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    tag.datasets.clear()
    tag.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_add_tags(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    tag_ids = request.data.get('tag_ids', [])
    tag_names = request.data.get('tags', [])

    for tag_id in tag_ids:
        try:
            tag = DatasetTag.objects.get(pk=tag_id, workspace=workspace)
            dataset.tag_objects.add(tag)
        except DatasetTag.DoesNotExist:
            pass

    for name in tag_names:
        tag, _ = DatasetTag.objects.get_or_create(name=name, workspace=workspace)
        dataset.tag_objects.add(tag)

    all_tags = list(dataset.tags or [])
    for name in tag_names:
        if name not in all_tags:
            all_tags.append(name)
    dataset.tags = all_tags
    dataset.save(update_fields=['tags', 'updated_at'])

    return Response(DatasetSerializer(dataset).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_remove_tags(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    tag_ids = request.data.get('tag_ids', [])
    tag_names = request.data.get('tags', [])

    for tag_id in tag_ids:
        try:
            tag = DatasetTag.objects.get(pk=tag_id, workspace=workspace)
            dataset.tag_objects.remove(tag)
        except DatasetTag.DoesNotExist:
            pass

    current_tags = list(dataset.tags or [])
    current_tags = [t for t in current_tags if t not in tag_names]
    dataset.tags = current_tags
    dataset.save(update_fields=['tags', 'updated_at'])

    return Response(DatasetSerializer(dataset).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dataset_versions(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        versions = DatasetVersion.objects.filter(dataset=dataset)
        serializer = DatasetVersionSerializer(versions, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        note = request.data.get('note', '')
        version_num = dataset.version + 1

        dataset.file.seek(0)
        file_content = dataset.file.read()
        dataset.file.seek(0)

        from django.core.files.base import ContentFile
        new_file = ContentFile(file_content, name=f"{dataset.file_name}_v{version_num}")

        version = DatasetVersion(
            dataset=dataset,
            version_number=version_num,
            file=new_file,
            file_name=dataset.file_name,
            file_size=dataset.file_size,
            file_hash=dataset.file_hash,
            analysis_context=dict(dataset.analysis_context),
            description=dataset.description,
            tags=list(dataset.tags),
            created_by=request.user,
            note=note,
        )
        version.save()

        dataset.version = version_num
        dataset.save(update_fields=['version', 'updated_at'])

        return Response(DatasetVersionSerializer(version).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_restore_version(request, pk, version_pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    try:
        version = DatasetVersion.objects.get(pk=version_pk, dataset=dataset)
    except DatasetVersion.DoesNotExist:
        return Response({"error": "Versión no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    dataset.file = version.file
    dataset.file_name = version.file_name
    dataset.file_size = version.file_size
    dataset.file_hash = version.file_hash
    dataset.analysis_context = version.analysis_context
    dataset.description = version.description
    dataset.tags = version.tags
    dataset.version = version.version_number
    dataset.save()

    return Response(DatasetSerializer(dataset).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_explore(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    ctx = dataset.analysis_context or {}
    return Response({
        "file_name": dataset.file_name,
        "summary": ctx.get("summary", {}),
        "columns": ctx.get("columns", []),
        "preview": ctx.get("preview", []),
        "kpis": ctx.get("kpis", {}),
        "charts": ctx.get("charts", {}),
        "health": ctx.get("health", {}),
        "correlations": ctx.get("correlations", {}),
        "cleaning": ctx.get("cleaning", []),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_preview(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    n = int(request.query_params.get('rows', 10))
    try:
        try:
            df = read_dataset_dataframe(dataset)
        except Exception as e:
            return Response({"error": f"No se pudo leer el dataset: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        preview = get_preview(df, n)
        return Response({"preview": preview, "total_rows": len(df), "columns": list(df.columns)})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_columns(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    cols = (dataset.analysis_context or {}).get("columns", [])
    return Response({"columns": cols})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_statistics(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    ctx = dataset.analysis_context or {}
    return Response({
        "summary": ctx.get("summary", {}),
        "kpis": ctx.get("kpis", {}),
        "health": ctx.get("health", {}),
        "correlations": ctx.get("correlations", {}),
        "anomalies": ctx.get("anomalies", {}),
        "trends": ctx.get("trends", {}),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_search(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    q = request.query_params.get('q', '')
    col = request.query_params.get('column', None)
    max_r = int(request.query_params.get('limit', 10))

    if not q:
        return Response({"error": "Se requiere un parámetro 'q'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        try:
            df = read_dataset_dataframe(dataset)
        except Exception as e:
            return Response({"error": f"No se pudo leer el dataset: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        results = search_records(df, q, col, max_r)
        return Response(results)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_membership_or_403(organization, user, roles_allowed=None):
    """Devuelve la Membership del usuario en la organización, o None si no
    pertenece o su rol no está en roles_allowed (cuando se especifica)."""
    m = Membership.objects.filter(organization=organization, user=user).first()
    if not m:
        return None
    if roles_allowed and m.role not in roles_allowed:
        return None
    return m


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def organization_list_create(request):
    """
    Módulo 1 — organizaciones y roles (antes: 1 usuario = 1 workspace, sin
    jerarquías ni forma de colaborar en equipo).
    """
    if request.method == 'GET':
        orgs = Organization.objects.filter(memberships__user=request.user).distinct()
        return Response(OrganizationSerializer(orgs, many=True, context={'request': request}).data)

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({"error": "El nombre de la organización es obligatorio"}, status=status.HTTP_400_BAD_REQUEST)
    org = Organization.objects.create(name=name, owner=request.user)
    Membership.objects.create(organization=org, user=request.user, role='owner')
    return Response(OrganizationSerializer(org, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def organization_detail(request, pk):
    try:
        org = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return Response({"error": "Organización no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    membership = _get_membership_or_403(org, request.user)
    if not membership:
        return Response({"error": "No perteneces a esta organización"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(OrganizationSerializer(org, context={'request': request}).data)

    if membership.role not in ('owner', 'admin'):
        return Response({"error": "Solo el propietario o un administrador pueden editar la organización"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        name = (request.data.get('name') or '').strip()
        if name:
            org.name = name
            org.save(update_fields=['name'])
        return Response(OrganizationSerializer(org, context={'request': request}).data)

    if request.method == 'DELETE':
        if membership.role != 'owner':
            return Response({"error": "Solo el propietario puede eliminar la organización"}, status=status.HTTP_403_FORBIDDEN)
        org.delete()
        return Response({"status": "ok"})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def organization_members(request, pk):
    try:
        org = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return Response({"error": "Organización no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    membership = _get_membership_or_403(org, request.user)
    if not membership:
        return Response({"error": "No perteneces a esta organización"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        members = org.memberships.select_related('user').all()
        return Response(MembershipSerializer(members, many=True).data)

    # POST: invitar a un usuario ya existente por email (sin envío de
    # correo real: el usuario debe ya tener cuenta en Nura)
    if membership.role not in ('owner', 'admin'):
        return Response({"error": "Solo el propietario o un administrador pueden invitar miembros"}, status=status.HTTP_403_FORBIDDEN)

    email = (request.data.get('email') or '').strip().lower()
    role = request.data.get('role', 'member')
    if role not in dict(Membership.ROLE_CHOICES):
        return Response({"error": "Rol inválido"}, status=status.HTTP_400_BAD_REQUEST)
    if role == 'owner':
        return Response({"error": "No se puede invitar directamente como propietario"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"error": "No existe ningún usuario registrado con ese email"}, status=status.HTTP_404_NOT_FOUND)

    if Membership.objects.filter(organization=org, user=target_user).exists():
        return Response({"error": "Ese usuario ya pertenece a la organización"}, status=status.HTTP_400_BAD_REQUEST)

    new_membership = Membership.objects.create(organization=org, user=target_user, role=role)
    return Response(MembershipSerializer(new_membership).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def organization_member_detail(request, pk, user_id):
    try:
        org = Organization.objects.get(pk=pk)
    except Organization.DoesNotExist:
        return Response({"error": "Organización no encontrada"}, status=status.HTTP_404_NOT_FOUND)

    membership = _get_membership_or_403(org, request.user)
    if not membership:
        return Response({"error": "No perteneces a esta organización"}, status=status.HTTP_404_NOT_FOUND)

    try:
        target_membership = Membership.objects.get(organization=org, user_id=user_id)
    except Membership.DoesNotExist:
        return Response({"error": "Ese usuario no pertenece a la organización"}, status=status.HTTP_404_NOT_FOUND)

    if membership.role not in ('owner', 'admin'):
        return Response({"error": "Solo el propietario o un administrador pueden gestionar miembros"}, status=status.HTTP_403_FORBIDDEN)

    if target_membership.role == 'owner':
        return Response({"error": "No se puede modificar ni eliminar al propietario"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        new_role = request.data.get('role')
        if new_role not in ('admin', 'member'):
            return Response({"error": "Rol inválido"}, status=status.HTTP_400_BAD_REQUEST)
        if membership.role != 'owner' and new_role == 'admin':
            return Response({"error": "Solo el propietario puede ascender a administrador"}, status=status.HTTP_403_FORBIDDEN)
        target_membership.role = new_role
        target_membership.save(update_fields=['role'])
        return Response(MembershipSerializer(target_membership).data)

    if request.method == 'DELETE':
        target_membership.delete()
        return Response({"status": "ok"})


# ============================================================
# MFA / 2FA (Módulo 1)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_setup(request):
    """Genera (o reutiliza) el secreto TOTP del usuario y devuelve la URI
    para escanear con una app tipo Google Authenticator/Authy. No activa
    el MFA todavía — eso requiere confirmar un código con /mfa/enable/."""
    import pyotp
    profile = request.user.profile
    if not profile.mfa_secret:
        profile.mfa_secret = pyotp.random_base32()
        profile.save(update_fields=['mfa_secret'])
    totp = pyotp.TOTP(profile.mfa_secret)
    uri = totp.provisioning_uri(name=request.user.email, issuer_name="Nura Intelligence")
    return Response({"secret": profile.mfa_secret, "otpauth_uri": uri, "mfa_enabled": profile.mfa_enabled})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_enable(request):
    import pyotp
    profile = request.user.profile
    code = (request.data.get('code') or '').strip()
    if not profile.mfa_secret:
        return Response({"error": "Primero llama a /auth/mfa/setup/"}, status=status.HTTP_400_BAD_REQUEST)
    totp = pyotp.TOTP(profile.mfa_secret)
    if not totp.verify(code, valid_window=1):
        return Response({"error": "Código incorrecto"}, status=status.HTTP_400_BAD_REQUEST)
    profile.mfa_enabled = True
    profile.save(update_fields=['mfa_enabled'])
    return Response({"status": "ok", "mfa_enabled": True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_disable(request):
    import pyotp
    profile = request.user.profile
    code = (request.data.get('code') or '').strip()
    if profile.mfa_enabled:
        totp = pyotp.TOTP(profile.mfa_secret)
        if not totp.verify(code, valid_window=1):
            return Response({"error": "Código incorrecto"}, status=status.HTTP_400_BAD_REQUEST)
    profile.mfa_enabled = False
    profile.mfa_secret = ''
    profile.save(update_fields=['mfa_enabled', 'mfa_secret'])
    return Response({"status": "ok", "mfa_enabled": False})


@api_view(['POST'])
@permission_classes([AllowAny])
def mfa_verify_login(request):
    """
    Segundo paso del login cuando el usuario tiene MFA activado.
    Recibe el `mfa_token` efímero emitido por /auth/login/ (ver
    NuraLoginView) junto con el código TOTP, y si es válido entrega los
    tokens JWT reales.
    """
    import pyotp
    from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

    mfa_token = request.data.get('mfa_token', '')
    code = (request.data.get('code') or '').strip()
    signer = TimestampSigner(salt='nura-mfa-login')
    try:
        user_id = signer.unsign(mfa_token, max_age=300)  # 5 minutos para completar el 2º factor
    except (BadSignature, SignatureExpired):
        return Response({"error": "Token de MFA inválido o expirado. Vuelve a iniciar sesión."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    profile = user.profile
    if not profile.mfa_enabled or not profile.mfa_secret:
        return Response({"error": "Este usuario no tiene MFA activado"}, status=status.HTTP_400_BAD_REQUEST)

    totp = pyotp.TOTP(profile.mfa_secret)
    if not totp.verify(code, valid_window=1):
        return Response({"error": "Código incorrecto"}, status=status.HTTP_400_BAD_REQUEST)

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login_view(request):
    """
    Reemplaza el login de dj-rest-auth SOLO para intercalar el segundo
    factor (MFA) antes de emitir tokens JWT reales. Si el usuario no tiene
    MFA activado, el comportamiento es idéntico al login normal.
    """
    from django.contrib.auth import authenticate
    from django.core.signing import TimestampSigner

    email = (request.data.get('email') or '').strip().lower()
    password = request.data.get('password') or ''
    if not email or not password:
        return Response({"error": "Email y contraseña son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=email, password=password)
    if user is None or not user.is_active:
        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_400_BAD_REQUEST)

    profile = user.profile
    if profile.mfa_enabled:
        signer = TimestampSigner(salt='nura-mfa-login')
        mfa_token = signer.sign(str(user.id))
        return Response({"mfa_required": True, "mfa_token": mfa_token})

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_filter(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    filters = request.data.get('filters', [])
    max_r = int(request.data.get('limit', 20))

    if not filters:
        return Response({"error": "Se requieren filtros"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        try:
            df = read_dataset_dataframe(dataset)
        except Exception as e:
            return Response({"error": f"No se pudo leer el dataset: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        results = filter_records(df, filters, max_r)
        return Response(results)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# Dashboards armables (Módulo 4)
# ---------------------------------------------------------------------------
# El "drag & drop" vive en el frontend como reordenamiento de una lista;
# aquí solo se persiste esa lista (`layout`) tal cual la manda el cliente.
# Cada widget es {"id", "kind": "kpi"|"chart", "title", "chart_type"?, "source"}.

def _widgets_from_dataset_context(context: dict) -> list:
    """Construye widgets de dashboard (KPIs + gráficos) a partir de un
    dataset_context ya calculado — la misma función que alimenta el chat y
    los reportes PDF/DOCX/PPTX, para no tener una tercera fuente de verdad."""
    import uuid as uuid_module
    widgets = []
    for kpi in (context.get('kpis') or [])[:6]:
        widgets.append({
            "id": uuid_module.uuid4().hex[:8],
            "kind": "kpi",
            "title": kpi.get("label", "KPI"),
            "source": {"value": kpi.get("value"), "type": kpi.get("type", "number")},
        })
    for chart in (context.get('charts') or []):
        widgets.append({
            "id": uuid_module.uuid4().hex[:8],
            "kind": "chart",
            "title": chart.get("column", "Gráfico"),
            "chart_type": chart.get("type"),
            "source": chart,
        })
    return widgets


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dashboard_list_create(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    if request.method == 'GET':
        dashboards = Dashboard.objects.filter(workspace=workspace)
        return Response(DashboardSerializer(dashboards, many=True).data)

    name = (request.data.get('name') or 'Mi Dashboard').strip() or 'Mi Dashboard'
    layout = request.data.get('layout', [])
    if not isinstance(layout, list):
        return Response({"error": "'layout' debe ser una lista de widgets"}, status=status.HTTP_400_BAD_REQUEST)

    dashboard = Dashboard.objects.create(
        workspace=workspace, name=name, layout=layout, created_by=request.user,
    )
    return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def dashboard_detail(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dashboard = Dashboard.objects.get(pk=pk, workspace=workspace)
    except Dashboard.DoesNotExist:
        return Response({"error": "Dashboard no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(DashboardSerializer(dashboard).data)

    if request.method == 'DELETE':
        dashboard.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH: usado tanto para renombrar como para guardar el nuevo orden
    # de widgets después de arrastrar y soltar en el frontend.
    name = request.data.get('name')
    layout = request.data.get('layout')
    if name is not None:
        dashboard.name = (name or '').strip() or dashboard.name
    if layout is not None:
        if not isinstance(layout, list):
            return Response({"error": "'layout' debe ser una lista de widgets"}, status=status.HTTP_400_BAD_REQUEST)
        dashboard.layout = layout
    dashboard.save()
    return Response(DashboardSerializer(dashboard).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dashboard_generate_ai(request):
    """
    Genera (o regenera) un dashboard automáticamente a partir del último
    análisis de un dataset: toma sus KPIs y gráficos ya calculados
    (`analysis_context`) y los convierte en widgets, sin que el usuario
    tenga que armarlo a mano.
    """
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    dataset_id = request.data.get('dataset_id')
    if not dataset_id:
        return Response({"error": "Se requiere 'dataset_id'"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        dataset = Dataset.objects.get(pk=dataset_id, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    context = dataset.analysis_context or {}
    if not context.get('kpis') and not context.get('charts'):
        # El dataset no fue analizado todavía (o no tiene columnas numéricas);
        # lo analizamos ahora mismo para no devolver un dashboard vacío.
        try:
            df = read_dataset_dataframe(dataset)
            df, _ = prepare_dataframe(df)
            context = {
                "kpis": get_kpis(df),
                "charts": get_chart_data(df),
            }
        except Exception as e:
            return Response({"error": f"No se pudo analizar el dataset: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    widgets = _widgets_from_dataset_context(context)
    if not widgets:
        return Response(
            {"error": "El dataset no tiene suficientes datos numéricos/categóricos para generar un dashboard."},
            status=status.HTTP_400_BAD_REQUEST
        )

    name = (request.data.get('name') or f"Dashboard IA — {dataset.file_name}").strip()
    dashboard_id = request.data.get('dashboard_id')
    if dashboard_id:
        try:
            dashboard = Dashboard.objects.get(pk=dashboard_id, workspace=workspace)
            dashboard.layout = widgets
            dashboard.dataset = dataset
            dashboard.is_ai_generated = True
            dashboard.save()
        except Dashboard.DoesNotExist:
            return Response({"error": "Dashboard no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    else:
        dashboard = Dashboard.objects.create(
            workspace=workspace, name=name, layout=widgets, dataset=dataset,
            is_ai_generated=True, created_by=request.user,
        )

    return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Triggers configurables (Módulo 5)
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def trigger_list_create(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)

    if request.method == 'GET':
        return Response(TriggerSerializer(Trigger.objects.filter(workspace=workspace), many=True).data)

    name = (request.data.get('name') or '').strip()
    event_type = request.data.get('event_type')
    action_type = request.data.get('action_type')
    config = request.data.get('config', {})

    if not name or not event_type or not action_type:
        return Response({"error": "Se requieren 'name', 'event_type' y 'action_type'"}, status=status.HTTP_400_BAD_REQUEST)
    if event_type not in dict(Trigger.EVENT_CHOICES):
        return Response({"error": f"event_type inválido. Opciones: {list(dict(Trigger.EVENT_CHOICES))}"}, status=status.HTTP_400_BAD_REQUEST)
    if action_type not in dict(Trigger.ACTION_CHOICES):
        return Response({"error": f"action_type inválido. Opciones: {list(dict(Trigger.ACTION_CHOICES))}"}, status=status.HTTP_400_BAD_REQUEST)
    if event_type == 'scheduled_date' and not (config or {}).get('scheduled_at'):
        return Response({"error": "Un trigger de 'scheduled_date' requiere config.scheduled_at (ISO 8601)"}, status=status.HTTP_400_BAD_REQUEST)

    trigger = Trigger.objects.create(
        workspace=workspace, name=name, event_type=event_type, action_type=action_type,
        config=config, created_by=request.user,
    )
    return Response(TriggerSerializer(trigger).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def trigger_detail(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        trigger = Trigger.objects.get(pk=pk, workspace=workspace)
    except Trigger.DoesNotExist:
        return Response({"error": "Trigger no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(TriggerSerializer(trigger).data)
    if request.method == 'DELETE':
        trigger.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    for field in ['name', 'event_type', 'action_type', 'config', 'active']:
        if field in request.data:
            setattr(trigger, field, request.data[field])
    trigger.save()
    return Response(TriggerSerializer(trigger).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_check_scheduled(request):
    """
    Evalúa los triggers de tipo 'scheduled_date' del workspace del usuario:
    si `config.scheduled_at` ya pasó y todavía no se disparó
    (`last_triggered_at` vacío), lo ejecuta. No hay Celery Beat configurado
    en este proyecto, así que este endpoint es lo que un scheduler externo
    (cron, un worker periódico) llamaría; se puede invocar a mano para
    simular ese paso, y así queda probado sin depender de infraestructura
    de scheduling adicional.
    """
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    from . import triggers as triggers_module

    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    now = timezone.now()
    fired = []

    pending = Trigger.objects.filter(workspace=workspace, event_type='scheduled_date', active=True, last_triggered_at__isnull=True)
    for trigger in pending:
        scheduled_at_raw = (trigger.config or {}).get('scheduled_at')
        scheduled_at = parse_datetime(scheduled_at_raw) if scheduled_at_raw else None
        if scheduled_at and scheduled_at <= now:
            dataset_id = (trigger.config or {}).get('dataset_id')
            dataset = Dataset.objects.filter(pk=dataset_id, workspace=workspace).first() if dataset_id else None
            logs = triggers_module.fire_triggers(workspace, 'scheduled_date', dataset=dataset)
            # fire_triggers dispara TODOS los triggers activos de este event_type;
            # acá solo nos interesa reportar si este trigger puntual corrió.
            fired.append(trigger.id)

    return Response({"fired_trigger_ids": fired, "checked_at": now.isoformat()})


# ---------------------------------------------------------------------------
# Compartir (Módulo 5) — datasets y dashboards, por usuario o por organización
# ---------------------------------------------------------------------------

def _validate_share_target(data):
    dataset_id = data.get('dataset_id')
    dashboard_id = data.get('dashboard_id')
    if bool(dataset_id) == bool(dashboard_id):
        return None, None, "Se requiere exactamente uno de 'dataset_id' o 'dashboard_id'"
    return dataset_id, dashboard_id, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_create(request):
    """
    Comparte un dataset o un dashboard propio con otro usuario (por email)
    o con toda una organización a la vez. El que comparte debe ser dueño
    del recurso (está en su propio workspace).
    """
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    dataset_id, dashboard_id, err = _validate_share_target(request.data)
    if err:
        return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

    permission = request.data.get('permission', 'view')
    if permission not in dict(SharedAccess.PERMISSION_CHOICES):
        return Response({"error": "permission debe ser 'view' o 'edit'"}, status=status.HTTP_400_BAD_REQUEST)

    dataset = dashboard = None
    if dataset_id:
        dataset = Dataset.objects.filter(pk=dataset_id, workspace=workspace).first()
        if not dataset:
            return Response({"error": "Dataset no encontrado en tu workspace"}, status=status.HTTP_404_NOT_FOUND)
    else:
        dashboard = Dashboard.objects.filter(pk=dashboard_id, workspace=workspace).first()
        if not dashboard:
            return Response({"error": "Dashboard no encontrado en tu workspace"}, status=status.HTTP_404_NOT_FOUND)

    target_email = (request.data.get('email') or '').strip().lower()
    org_id = request.data.get('organization_id')
    if bool(target_email) == bool(org_id):
        return Response({"error": "Se requiere exactamente uno de 'email' u 'organization_id'"}, status=status.HTTP_400_BAD_REQUEST)

    shared_with = shared_with_org = None
    if target_email:
        shared_with = get_user_model().objects.filter(email__iexact=target_email).first()
        if not shared_with:
            return Response({"error": "No existe un usuario con ese email"}, status=status.HTTP_404_NOT_FOUND)
        if shared_with.id == request.user.id:
            return Response({"error": "No podés compartir un recurso con vos mismo"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        shared_with_org = Organization.objects.filter(
            pk=org_id, memberships__user=request.user
        ).first()
        if not shared_with_org:
            return Response({"error": "No pertenecés a esa organización"}, status=status.HTTP_404_NOT_FOUND)

    try:
        share = SharedAccess.objects.create(
            dataset=dataset, dashboard=dashboard, shared_with=shared_with,
            shared_with_org=shared_with_org, shared_by=request.user, permission=permission,
        )
    except IntegrityError:
        return Response({"error": "Ya está compartido con ese destinatario"}, status=status.HTTP_409_CONFLICT)

    return Response(SharedAccessSerializer(share).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def share_list(request):
    """Lista lo que el usuario compartió y lo que otros compartieron con él
    (directamente o a través de una organización a la que pertenece)."""
    my_org_ids = Organization.objects.filter(memberships__user=request.user).values_list('id', flat=True)
    shared_by_me = SharedAccess.objects.filter(shared_by=request.user)
    shared_with_me = SharedAccess.objects.filter(
        Q(shared_with=request.user) | Q(shared_with_org_id__in=my_org_ids)
    ).exclude(shared_by=request.user)
    return Response({
        "shared_by_me": SharedAccessSerializer(shared_by_me, many=True).data,
        "shared_with_me": SharedAccessSerializer(shared_with_me, many=True).data,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def share_revoke(request, pk):
    share = SharedAccess.objects.filter(pk=pk, shared_by=request.user).first()
    if not share:
        return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
    share.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _accessible_dataset_ids(user):
    """IDs de datasets propios + compartidos con el usuario (directo u org)."""
    my_org_ids = Organization.objects.filter(memberships__user=user).values_list('id', flat=True)
    shared_ids = SharedAccess.objects.filter(
        Q(shared_with=user) | Q(shared_with_org_id__in=my_org_ids)
    ).exclude(dataset__isnull=True).values_list('dataset_id', flat=True)
    return list(shared_ids)


def _accessible_dashboard_ids(user):
    my_org_ids = Organization.objects.filter(memberships__user=user).values_list('id', flat=True)
    shared_ids = SharedAccess.objects.filter(
        Q(shared_with=user) | Q(shared_with_org_id__in=my_org_ids)
    ).exclude(dashboard__isnull=True).values_list('dashboard_id', flat=True)
    return list(shared_ids)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shared_datasets_list(request):
    """Datasets que OTROS compartieron con el usuario (no los propios)."""
    ids = _accessible_dataset_ids(request.user)
    datasets = Dataset.objects.filter(id__in=ids)
    return Response(DatasetSerializer(datasets, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shared_dashboards_list(request):
    """Dashboards que OTROS compartieron con el usuario (no los propios)."""
    ids = _accessible_dashboard_ids(request.user)
    dashboards = Dashboard.objects.filter(id__in=ids)
    return Response(DashboardSerializer(dashboards, many=True).data)


# ---------------------------------------------------------------------------
# Comentarios (Módulo 5)
# ---------------------------------------------------------------------------

def _user_can_access_dataset(user, dataset):
    if dataset.workspace.owner_id == user.id:
        return True
    return dataset.id in _accessible_dataset_ids(user)


def _user_can_access_dashboard(user, dashboard):
    if dashboard.workspace.owner_id == user.id:
        return True
    return dashboard.id in _accessible_dashboard_ids(user)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comment_list_create(request):
    dataset_id = request.query_params.get('dataset_id') or request.data.get('dataset_id')
    dashboard_id = request.query_params.get('dashboard_id') or request.data.get('dashboard_id')
    if bool(dataset_id) == bool(dashboard_id):
        return Response({"error": "Se requiere exactamente uno de 'dataset_id' o 'dashboard_id'"}, status=status.HTTP_400_BAD_REQUEST)

    dataset = dashboard = None
    if dataset_id:
        dataset = Dataset.objects.filter(pk=dataset_id).first()
        if not dataset or not _user_can_access_dataset(request.user, dataset):
            return Response({"error": "Dataset no encontrado o sin acceso"}, status=status.HTTP_404_NOT_FOUND)
    else:
        dashboard = Dashboard.objects.filter(pk=dashboard_id).first()
        if not dashboard or not _user_can_access_dashboard(request.user, dashboard):
            return Response({"error": "Dashboard no encontrado o sin acceso"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        comments = Comment.objects.filter(dataset=dataset) if dataset else Comment.objects.filter(dashboard=dashboard)
        return Response(CommentSerializer(comments, many=True).data)

    body = (request.data.get('body') or '').strip()
    if not body:
        return Response({"error": "El comentario no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST)
    comment = Comment.objects.create(dataset=dataset, dashboard=dashboard, author=request.user, body=body)
    return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def comment_delete(request, pk):
    comment = Comment.objects.filter(pk=pk, author=request.user).first()
    if not comment:
        return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Agentes por área de negocio (Módulo 6)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agents_by_area(request):
    """Expone el registro de agentes especializados agrupado por área de
    negocio (finanzas/ventas/marketing/operaciones/general), para que el
    frontend pueda mostrar "elegí un área" en vez de una lista plana."""
    from ai.agents import get_agents_by_business_area

    grouped = get_agents_by_business_area()
    return Response({
        area: [
            {"key": a.key, "name": a.name, "focus": a.focus, "priority": a.priority}
            for a in agents
        ]
        for area, agents in grouped.items()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_what_if(request, pk):
    """
    Módulo 6 — simulaciones "qué pasa si...". Body:
        {"target_col": "ventas", "periods": 3, "scenarios": [
            {"name": "Crecer 20% más rápido", "growth_adjustment_pct": 20},
            {"name": "Bajar el precio 10%", "variable": "precio", "change_pct": -10}
        ]}
    """
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    try:
        dataset = Dataset.objects.get(pk=pk, workspace=workspace)
    except Dataset.DoesNotExist:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    target_col = request.data.get('target_col')
    periods = int(request.data.get('periods', 3))
    scenarios = request.data.get('scenarios', [])

    if not target_col:
        return Response({"error": "Se requiere 'target_col'"}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(scenarios, list) or not scenarios:
        return Response({"error": "Se requiere al menos un escenario en 'scenarios'"}, status=status.HTTP_400_BAD_REQUEST)
    if periods < 1 or periods > 24:
        return Response({"error": "'periods' debe estar entre 1 y 24"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        df = read_dataset_dataframe(dataset)
    except Exception as e:
        return Response({"error": f"No se pudo leer el dataset: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    if target_col not in df.columns:
        return Response({"error": f"'{target_col}' no existe en este dataset"}, status=status.HTTP_400_BAD_REQUEST)

    result = what_if_simulation(df, target_col, scenarios, periods=periods)
    if "error" in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


# ---------------------------------------------------------------------------
# Recomendaciones proactivas (Módulo 6)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendation_list(request):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    recs = Recommendation.objects.filter(workspace=workspace)
    if request.query_params.get('dismissed') != 'true':
        recs = recs.filter(dismissed=False)
    dataset_id = request.query_params.get('dataset_id')
    if dataset_id:
        recs = recs.filter(dataset_id=dataset_id)
    return Response(RecommendationSerializer(recs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recommendation_dismiss(request, pk):
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    rec = Recommendation.objects.filter(pk=pk, workspace=workspace).first()
    if not rec:
        return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
    rec.dismissed = True
    rec.save(update_fields=['dismissed'])
    return Response(RecommendationSerializer(rec).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dataset_generate_recommendations(request, pk):
    """Regenera recomendaciones a demanda (normalmente ya corre solo al
    terminar el análisis async; este endpoint es para forzarlo a mano, o
    para cuando el dataset se analizó antes de que este módulo existiera)."""
    workspace, _ = Workspace.objects.get_or_create(owner=request.user)
    dataset = Dataset.objects.filter(pk=pk, workspace=workspace).first()
    if not dataset:
        return Response({"error": "Dataset no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if not dataset.analysis_context:
        return Response({"error": "Este dataset todavía no tiene un análisis para generar recomendaciones"}, status=status.HTTP_400_BAD_REQUEST)

    from . import recommendations as recommendations_module
    created = recommendations_module.generate_recommendations_for_dataset(dataset)
    return Response(RecommendationSerializer(created, many=True).data, status=status.HTTP_201_CREATED)
