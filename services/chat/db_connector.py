"""
Módulo 2 — carga de datos desde bases de datos externas.

Diseño de seguridad deliberado (por esto se había pospuesto una primera
versión apurada):
- Las credenciales de conexión NUNCA se guardan: viajan en el body del
  request, se usan para una sola consulta, y se descartan. No existe un
  modelo "Connection" con contraseñas persistidas.
- Solo se permite una única sentencia `SELECT` de lectura. Se rechaza
  cualquier texto que contenga palabras clave de escritura/DDL
  (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/GRANT/EXEC...), punto y
  coma (para evitar apilar sentencias) o comentarios SQL.
- La conexión se abre en modo solo-lectura cuando el dialecto lo soporta
  (Postgres), con un timeout corto, y se cierra siempre en el `finally`.
- Los resultados se limitan a un máximo de filas para no agotar memoria.
"""
import ipaddress
import re
import socket
from typing import Tuple

MAX_ROWS = 50_000
CONNECT_TIMEOUT_SECONDS = 10

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|exec|execute|call|merge|replace|into\s+outfile)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(ValueError):
    pass


def validate_select_only(query: str) -> str:
    """Lanza UnsafeQueryError si la consulta no es un SELECT de solo lectura."""
    q = (query or "").strip()
    if not q:
        raise UnsafeQueryError("La consulta no puede estar vacía.")
    if ";" in q.rstrip(";"):
        raise UnsafeQueryError("No se permite más de una sentencia (detectado ';' en medio de la consulta).")
    if "--" in q or "/*" in q:
        raise UnsafeQueryError("No se permiten comentarios SQL en la consulta.")
    if not re.match(r"^\s*(select|with)\b", q, re.IGNORECASE):
        raise UnsafeQueryError("Solo se permiten consultas que empiecen con SELECT (o WITH ... SELECT).")
    if _FORBIDDEN_KEYWORDS.search(q):
        raise UnsafeQueryError("La consulta contiene una palabra clave no permitida (solo se permite lectura).")
    return q.rstrip(";")


# FIXED: 2026-10-12 SSRF — `dataset_import_db` dejaba a cualquier usuario
# autenticado (sin restriccion adicional de rol/organizacion) decirle al
# servidor a qué `host`/`port` conectarse. Aunque la consulta en si estaba
# bien validada (solo SELECT), no habia ninguna validacion sobre el DESTINO
# de la conexion: un usuario podia apuntar a 'localhost', a la IP de
# metadata de la nube (169.254.169.254) o a cualquier host interno de la
# VPC y usar el propio backend de Nura como proxy de red (SSRF) para
# sondear o leer servicios que no deberian ser alcanzables desde fuera.
# Esta funcion resuelve el host y rechaza loopback/link-local/privado/
# reservado antes de intentar conectar.
def _assert_host_is_public(host: str) -> None:
    hostname = (host or "").strip().strip("[]")
    if not hostname:
        raise UnsafeQueryError("Host inválido.")
    if hostname.lower() in ("localhost", "0.0.0.0", "::1", "metadata.google.internal"):
        raise UnsafeQueryError("No se permite conectar a hosts internos/locales.")
    try:
        resolved = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        raise UnsafeQueryError(f"No se pudo resolver el host '{hostname}'.")
    for addr in resolved:
        ip = ipaddress.ip_address(addr)
        if (ip.is_loopback or ip.is_private or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise UnsafeQueryError(
                "No se permite conectar a direcciones IP privadas, de loopback "
                "o reservadas (riesgo de SSRF)."
            )


def build_safe_connection_url(dialect: str, host: str, port: str, database: str, username: str, password: str) -> str:
    from urllib.parse import quote_plus

    dialect = (dialect or "").strip().lower()
    drivers = {
        "postgresql": "postgresql+psycopg2",
        "postgres": "postgresql+psycopg2",
        "mysql": "mysql+pymysql",
    }
    driver = drivers.get(dialect)
    if not driver:
        raise UnsafeQueryError(f"Motor de base de datos no soportado: '{dialect}'. Usa 'postgresql' o 'mysql'.")

    _assert_host_is_public(host)

    user = quote_plus(username or "")
    pwd = quote_plus(password or "")
    return f"{driver}://{user}:{pwd}@{host}:{port}/{database}"


def run_read_only_query(connection_url: str, query: str):
    """
    Ejecuta una consulta SELECT validada contra una base de datos externa y
    devuelve un DataFrame de pandas. La conexión se abre y se cierra en
    esta misma función — nunca se guarda en ningún lado.
    """
    import pandas as pd
    from sqlalchemy import create_engine, text

    safe_query = validate_select_only(query)

    engine = create_engine(connection_url, connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS}) \
        if "mysql" in connection_url else \
        create_engine(connection_url, connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS, "options": "-c default_transaction_read_only=on"})

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(text(safe_query), conn)
    finally:
        engine.dispose()

    if len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS)
    return df
