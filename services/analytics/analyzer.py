from typing import Dict, Any, List, Tuple
import re
import json
import pandas as pd
import numpy as np
from .utils import detect_file_type
from .scoring import evaluate_business
from .trends import analyze_numeric_trends
from .anomalies import detect_anomalies, check_fraud_signals
from .forecasting import simple_forecast
from .cleaning import clean_dataframe, detect_headers, detect_language


def _is_valid_header_row(values):
    # Antes: `not values` con un pandas Index de más de un elemento lanza
    # "ValueError: truth value of a Index is ambiguous" — bug real que
    # rompía cualquier archivo que pasara por el fallback de CSV.
    if values is None or len(values) < 2:
        return False
    str_vals = [str(v).strip() for v in values if pd.notna(v)]
    if not str_vals:
        return False
    all_numeric = all(re.match(r'^-?\d+(\.\d+)?$', v) for v in str_vals)
    if all_numeric:
        return False
    empty_count = sum(1 for v in str_vals if v == '' or v.startswith('Unnamed'))
    if empty_count / max(len(str_vals), 1) > 0.5:
        return False
    unique_ratio = len(set(str_vals)) / max(len(str_vals), 1)
    if unique_ratio < 0.5 and len(str_vals) > 3:
        return False
    return True


def _json_to_dataframe(raw) -> pd.DataFrame:
    """
    Convierte contenido JSON ya parseado (list/dict) a un DataFrame tabular.
    Soporta las formas más comunes:
      - Lista de objetos:            [{"a": 1}, {"a": 2}]
      - Objeto contenedor:           {"data": [...]} / {"results": [...]} / {"items": [...]}
      - Objeto único:                {"a": 1, "b": 2}
      - Diccionario de columnas:     {"a": [1, 2], "b": [3, 4]}
      - Lista de valores simples:    [1, 2, 3]
    """
    if isinstance(raw, list):
        if not raw:
            raise ValueError("El JSON es una lista vacía.")
        if all(isinstance(item, dict) for item in raw):
            return pd.json_normalize(raw)
        # Lista de valores simples (no objetos)
        return pd.DataFrame({"value": raw})

    if isinstance(raw, dict):
        # Contenedor típico de una API: {"data": [...]}, {"results": [...]}, etc.
        for key in ("data", "results", "items", "records", "rows"):
            value = raw.get(key)
            if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                return pd.json_normalize(value)

        # ¿Es un dict de columnas? (todas las claves apuntan a listas de igual longitud)
        list_values = [v for v in raw.values() if isinstance(v, list)]
        if list_values and len(list_values) == len(raw) and len({len(v) for v in list_values}) == 1:
            return pd.DataFrame(raw)

        # Objeto único -> una fila
        return pd.json_normalize([raw])

    raise ValueError("El JSON no contiene una estructura de datos reconocible (se esperaba una lista o un objeto).")


def load_csv(file_obj) -> pd.DataFrame:
    file_type = (detect_file_type(file_obj) or "").strip().lower()

    def _read_csv_fallback() -> pd.DataFrame:
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "utf-16"]
        separators = [",", ";", "\t", "|"]
        best_df = None
        best_score = -1
        last_err: Exception | None = None
        for enc in encodings:
            for sep in separators:
                try:
                    try:
                        file_obj.seek(0)
                    except Exception:
                        pass
                    df = pd.read_csv(file_obj, encoding=enc, sep=sep)
                    if df is None or df.empty or len(df.columns) == 0:
                        raise ValueError("No columns parsed from CSV.")
                    score = len(df.columns) * 10 + len(df)
                    if _is_valid_header_row(df.columns):
                        score += 500
                    if score > best_score:
                        best_score = score
                        best_df = df
                except Exception as e:
                    last_err = e
        if best_df is not None:
            return best_df
        raise ValueError(f"CSV no compatible o vacío. Error original: {last_err}") from last_err

    if file_type in [".xlsx", ".xls"]:
        try:
            try:
                file_obj.seek(0)
            except Exception:
                pass
            df = pd.read_excel(file_obj)
        except Exception as e:
            raise ValueError(f"No se pudo leer el archivo Excel: {e}") from e
        if df is None or df.empty or len(df.columns) == 0:
            raise ValueError("El Excel está vacío o no contiene columnas válidas.")
        df, headers_fixed = detect_headers(df)
        return df

    if file_type == ".json":
        # Antes: los .json pasaban la validación de subida pero nunca se
        # convertían de verdad en un DataFrame — caían al parser de CSV de
        # abajo, que intentaba leer el JSON como si fuera texto separado
        # por comas (fallaba o producía análisis sin sentido).
        try:
            file_obj.seek(0)
        except Exception:
            pass
        try:
            raw = json.load(file_obj)
        except json.JSONDecodeError as e:
            raise ValueError(f"El archivo JSON no es válido: {e}") from e
        df = _json_to_dataframe(raw)
        if df is None or df.empty or len(df.columns) == 0:
            raise ValueError("El JSON no contiene datos tabulares reconocibles.")
        df, headers_fixed = detect_headers(df)
        return df

    df = _read_csv_fallback()
    df, headers_fixed = detect_headers(df)
    return df


def prepare_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    language = detect_language(df.columns.tolist())
    original_shape = df.shape
    df, cleaning_changes, date_cols = clean_dataframe(df)
    final_shape = df.shape
    return df, {
        "original_rows": original_shape[0],
        "original_columns": original_shape[1],
        "final_rows": final_shape[0],
        "final_columns": final_shape[1],
        "language": language,
        "date_columns": date_cols,
        "changes": cleaning_changes,
        "total_changes": len(cleaning_changes),
    }


def _infer_semantic_type(col_name: str, dtype_str: str) -> str:
    col_lower = col_name.lower()
    if any(word in col_lower for word in ["precio", "price", "costo", "cost", "monto", "amount", "total", "subtotal", "tax", "impuesto", "profit", "ganancia", "margen", "margin", "ingreso", "revenue"]):
        return "Financiero"
    if any(word in col_lower for word in ["ventas", "sales", "pedido", "order", "invoice", "factura", "transaccion", "transaction", "compra", "purchase"]):
        return "Ventas"
    if any(word in col_lower for word in ["fecha", "date", "tiempo", "time", "año", "year", "mes", "month", "dia", "day", "hora", "hour", "created", "updated", "timestamp"]):
        return "Temporal"
    if any(word in col_lower for word in ["id", "codigo", "code", "sku", "uuid", "pk", "fk", "key", "llave"]):
        return "Identificador"
    if any(word in col_lower for word in ["cliente", "client", "customer", "usuario", "user", "lead", "prospecto", "contacto", "email", "correo", "nombre", "name", "apellido", "phone", "telefono"]):
        return "Clientes"
    if any(word in col_lower for word in ["categoria", "category", "tipo", "type", "estado", "status", "producto", "product", "region", "pais", "country", "ciudad", "city", "canal", "channel", "brand", "marca", "modelo", "model"]):
        return "Dimensión Categórica"
    if any(word in col_lower for word in ["cantidad", "quantity", "qty", "volumen", "volume", "peso", "weight", "stock", "inventario", "units", "unidades"]):
        return "Métrica/Cantidad"
    if any(word in col_lower for word in ["riesgo", "risk", "churn", "fraude", "fraud", "error", "falla", "failure", "alert", "alerta", "warning", "advertencia", "atraso", "delay", "mora"]):
        return "Riesgo"
    if "object" in dtype_str or "str" in dtype_str:
        return "Texto/Categoría"
    elif "int" in dtype_str or "float" in dtype_str:
        return "Numérico Genérico"
    return "Desconocido"


def detect_industry(df: pd.DataFrame) -> str:
    cols = [c.lower() for c in df.columns]
    industries = {
        "Ecommerce": ["order", "pedido", "cart", "carrito", "sku", "shipping", "envio", "delivery", "product", "producto", "variant", "variante", "stock", "inventory", "tienda", "store"],
        "SaaS": ["subscription", "suscripcion", "plan", "mrr", "arr", "churn", "trial", "prueba", "user_id", "active", "feature", "upgrade", "license", "licencia", "recurring", "recurrente"],
        "Finanzas": ["transaction", "transaccion", "balance", "account", "cuenta", "credit", "debito", "debit", "loan", "prestamo", "interest", "interes", "asset", "activo", "liability", "pasivo", "investment", "inversion"],
        "Marketing": ["campaign", "campaña", "click", "impression", "impresion", "ctr", "cpc", "conversion", "lead", "source", "fuente", "medium", "medio", "ad_group", "keyword", "reach", "alcance"],
        "Recursos Humanos": ["employee", "empleado", "payroll", "nomina", "salary", "salario", "department", "departamento", "hiring", "contratacion", "turnover", "performance", "desempeño", "vacation", "vacaciones", "bonus", "bono"]
    }
    scores = {industry: 0 for industry in industries}
    for industry, keywords in industries.items():
        for keyword in keywords:
            if any(keyword in col for col in cols):
                scores[industry] += 2
            if industry.lower() in cols:
                scores[industry] += 5
    best_industry = max(scores, key=scores.get)
    if scores[best_industry] > 0:
        return best_industry
    return "General / Negocios"


def get_business_context(df: pd.DataFrame, industry: str) -> str:
    cols_info = column_info(df)
    semantic_counts = {}
    for col, info in cols_info.items():
        stype = info["semantic_type"]
        semantic_counts[stype] = semantic_counts.get(stype, 0) + 1
    context_parts = [f"Este es un dataset de tipo {industry}."]
    if semantic_counts.get("Financiero", 0) > 0 or semantic_counts.get("Ventas", 0) > 0:
        context_parts.append("Contiene información financiera y de transacciones comerciales.")
    if semantic_counts.get("Clientes", 0) > 0:
        context_parts.append("Incluye datos detallados de clientes o usuarios.")
    if semantic_counts.get("Riesgo", 0) > 0:
        context_parts.append("Se detectaron indicadores de riesgo o señales de alerta.")
    if semantic_counts.get("Temporal", 0) > 0:
        context_parts.append("La información tiene un componente temporal para análisis de tendencias.")
    return " ".join(context_parts)


def column_info(df: pd.DataFrame) -> Dict[str, Any]:
    info = {}
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        info[col] = {
            "dtype": dtype_str,
            "semantic_type": _infer_semantic_type(col, dtype_str),
            "missing": int(df[col].isna().sum()),
            "unique": int(df[col].nunique()),
        }
    return info


def compute_correlations(df: pd.DataFrame, threshold: float = 0.5) -> List[Dict[str, Any]]:
    correlations = []
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2:
        return correlations
    corr_matrix = numeric_df.corr()
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            col1 = corr_matrix.columns[i]
            col2 = corr_matrix.columns[j]
            corr_value = corr_matrix.iloc[i, j]
            if pd.notna(corr_value) and abs(corr_value) >= threshold:
                strength = "Muy Fuerte" if abs(corr_value) >= 0.85 else ("Fuerte" if abs(corr_value) >= 0.7 else "Moderada")
                correlations.append({
                    "col1": col1,
                    "col2": col2,
                    "correlation": round(float(corr_value), 2),
                    "strength": strength,
                    "direction": "Positiva" if corr_value > 0 else "Negativa"
                })
    correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return correlations


def detect_critical_variables(df: pd.DataFrame) -> List[Dict[str, Any]]:
    corrs = compute_correlations(df, threshold=0.6)
    influence_counts = {}
    for c in corrs:
        influence_counts[c["col1"]] = influence_counts.get(c["col1"], 0) + 1
        influence_counts[c["col2"]] = influence_counts.get(c["col2"], 0) + 1
    critical = []
    for col, count in influence_counts.items():
        if count >= 2:
            critical.append({
                "column": col,
                "influence_score": count,
                "importance": "Alta" if count >= 4 else "Media"
            })
    critical.sort(key=lambda x: x["influence_score"], reverse=True)
    return critical


def dataset_summary(df: pd.DataFrame) -> Dict[str, Any]:
    rows, cols = df.shape
    total_missing = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    return {
        "rows": rows,
        "columns": cols,
        "total_missing": total_missing,
        "duplicate_rows": duplicate_rows,
    }


def get_preview(df: pd.DataFrame, n: int = 10) -> List[Dict[str, Any]]:
    return df.head(n).replace({np.nan: None}).to_dict(orient="records")


def get_chart_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    charts = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns[:3]
    for col in numeric_cols:
        series = df[col].dropna()
        if not series.empty:
            charts.append({
                "type": "distribution",
                "column": col,
                "data": series.tolist()[:100]
            })
    cat_cols = df.select_dtypes(include=["object", "category"]).columns[:3]
    for col in cat_cols:
        counts = df[col].value_counts().head(5)
        if not counts.empty:
            charts.append({
                "type": "categorical",
                "column": col,
                "labels": counts.index.tolist(),
                "values": counts.values.tolist()
            })

    all_numeric_cols = df.select_dtypes(include=[np.number]).columns
    # Heatmap de correlación — hasta 8 columnas numéricas para que siga siendo legible
    if len(all_numeric_cols) >= 2:
        heat_cols = list(all_numeric_cols[:8])
        corr_matrix = df[heat_cols].corr()
        cells = []
        for r in heat_cols:
            for c in heat_cols:
                val = corr_matrix.loc[r, c]
                cells.append({"row": r, "col": c, "value": round(float(val), 2) if pd.notna(val) else 0})
        charts.append({
            "type": "heatmap",
            "column": "Correlación entre variables",
            "labels": heat_cols,
            "cells": cells,
        })

    # Scatter — el par de columnas numéricas con mayor correlación absoluta
    if len(all_numeric_cols) >= 2:
        best_pair = None
        best_corr = -1
        corr_matrix = df[all_numeric_cols].corr()
        for i in range(len(all_numeric_cols)):
            for j in range(i + 1, len(all_numeric_cols)):
                c1, c2 = all_numeric_cols[i], all_numeric_cols[j]
                val = corr_matrix.loc[c1, c2]
                if pd.notna(val) and abs(val) > best_corr:
                    best_corr = abs(val)
                    best_pair = (c1, c2)
        if best_pair:
            c1, c2 = best_pair
            sample = df[[c1, c2]].dropna().head(200)
            charts.append({
                "type": "scatter",
                "column": f"{c1} vs {c2}",
                "x_label": c1,
                "y_label": c2,
                "points": [{"x": float(x), "y": float(y)} for x, y in zip(sample[c1], sample[c2])],
            })

    return charts


def get_kpis(df: pd.DataFrame) -> List[Dict[str, Any]]:
    kpis = []
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return kpis
    for col in numeric_df.columns:
        col_lower = col.lower()
        if any(w in col_lower for w in ["total", "monto", "amount", "revenue", "ventas", "sales", "profit", "ganancia"]):
            kpis.append({
                "label": f"Total {col}",
                "value": round(float(numeric_df[col].sum()), 2),
                "type": "currency"
            })
            kpis.append({
                "label": f"Promedio {col}",
                "value": round(float(numeric_df[col].mean()), 2),
                "type": "currency"
            })
        elif any(w in col_lower for w in ["count", "cantidad", "qty", "items", "unidades", "units"]):
            kpis.append({
                "label": f"Volumen {col}",
                "value": int(numeric_df[col].sum()),
                "type": "number"
            })
    if not kpis:
        kpis.append({
            "label": "Registros Totales",
            "value": len(df),
            "type": "number"
        })
        kpis.append({
            "label": "Columnas Analizadas",
            "value": len(df.columns),
            "type": "number"
        })
    return kpis[:4]


def search_records(df: pd.DataFrame, query: str, column: str = None, max_results: int = 10) -> List[Dict[str, Any]]:
    query_lower = query.lower()
    if column and column in df.columns:
        mask = df[column].astype(str).str.lower().str.contains(query_lower, na=False)
        results = df[mask].head(max_results)
    else:
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query_lower, na=False).any(), axis=1)
        results = df[mask].head(max_results)
    return {
        "total_matches": int(mask.sum()),
        "showing": min(int(mask.sum()), max_results),
        "records": results.replace({np.nan: None}).to_dict(orient="records")
    }


def filter_records(df: pd.DataFrame, filters: List[Dict[str, Any]], max_results: int = 20) -> List[Dict[str, Any]]:
    mask = pd.Series(True, index=df.index)
    for f in filters:
        col = f.get("column", "")
        op = f.get("operator", "eq")
        val = f.get("value", "")
        if col not in df.columns:
            continue
        try:
            if op == "eq":
                mask &= df[col].astype(str).str.lower() == str(val).lower()
            elif op == "gt":
                mask &= pd.to_numeric(df[col], errors='coerce') > float(val)
            elif op == "lt":
                mask &= pd.to_numeric(df[col], errors='coerce') < float(val)
            elif op == "gte":
                mask &= pd.to_numeric(df[col], errors='coerce') >= float(val)
            elif op == "lte":
                mask &= pd.to_numeric(df[col], errors='coerce') <= float(val)
            elif op == "contains":
                mask &= df[col].astype(str).str.lower().str.contains(str(val).lower(), na=False)
            elif op == "ne":
                mask &= df[col].astype(str).str.lower() != str(val).lower()
        except Exception:
            continue
    results = df[mask].head(max_results)
    return {
        "total_matches": int(mask.sum()),
        "showing": min(int(mask.sum()), max_results),
        "records": results.replace({np.nan: None}).to_dict(orient="records")
    }
