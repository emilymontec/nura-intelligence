import pandas as pd
import numpy as np
from typing import Dict, List, Any


def simple_forecast(df: pd.DataFrame, target_col: str, periods: int = 3) -> Dict[str, Any]:
    if target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
        return {}
    series = df[target_col].dropna().values
    if len(series) < 3:
        return {}
    x = np.arange(len(series))
    y = series
    slope, intercept = np.polyfit(x, y, 1)
    last_val = series[-1]
    projections = []
    for i in range(1, periods + 1):
        next_val = intercept + slope * (len(series) + i - 1)
        projections.append(round(float(max(0, next_val)), 2))
    growth_rate = (projections[-1] - last_val) / last_val if last_val != 0 else 0
    return {
        "column": target_col,
        "current_value": float(last_val),
        "projections": projections,
        "trend_slope": float(slope),
        "expected_growth": round(float(growth_rate * 100), 2)
    }


def what_if_simulation(df: pd.DataFrame, target_col: str, scenarios: List[Dict[str, Any]], periods: int = 3) -> Dict[str, Any]:
    """
    Módulo 6 — simulaciones "qué pasa si...". Parte del mismo pronóstico
    lineal de `simple_forecast` como línea base y aplica, por escenario,
    uno de dos ajustes:

    - `growth_adjustment_pct`: desplaza directamente la tasa de crecimiento
      proyectada (ej. "¿y si crecemos 20% más rápido?").
    - `variable` + `change_pct`: estima el efecto de cambiar OTRA columna
      numérica (ej. "¿y si bajo el precio 10%?") usando la correlación
      histórica entre esa variable y `target_col` como proxy de elasticidad.
      Es una heurística explícita, no un modelo causal — se devuelve la
      correlación usada para que quede claro de dónde sale el número, y el
      efecto se limita a ±80% para no proyectar disparates cuando la
      correlación es alta pero el cambio pedido es extremo.
    """
    baseline = simple_forecast(df, target_col, periods)
    if not baseline:
        return {"error": f"No se pudo generar un pronóstico base para '{target_col}' (se requieren al menos 3 valores numéricos)."}

    results = []
    for scenario in scenarios or []:
        name = scenario.get("name", "Escenario")

        if "growth_adjustment_pct" in scenario:
            adj = float(scenario["growth_adjustment_pct"]) / 100
            adjusted = [round(p * (1 + adj), 2) for p in baseline["projections"]]
            results.append({
                "name": name,
                "method": "ajuste_directo_de_crecimiento",
                "growth_adjustment_pct": scenario["growth_adjustment_pct"],
                "projections": adjusted,
            })
            continue

        variable = scenario.get("variable")
        change_pct = scenario.get("change_pct")
        if variable is None or change_pct is None:
            results.append({"name": name, "error": "Escenario inválido: requiere 'growth_adjustment_pct' o ('variable' y 'change_pct')"})
            continue
        if variable not in df.columns or not pd.api.types.is_numeric_dtype(df[variable]) or variable == target_col:
            results.append({"name": name, "error": f"'{variable}' no es una columna numérica válida (distinta de '{target_col}') en este dataset"})
            continue

        pair = df[[variable, target_col]].dropna()
        corr = float(pair[variable].corr(pair[target_col])) if len(pair) >= 3 else 0.0
        if pd.isna(corr):
            corr = 0.0

        raw_effect_pct = corr * float(change_pct)
        effect_pct = max(-80.0, min(80.0, raw_effect_pct))
        adjusted = [round(p * (1 + effect_pct / 100), 2) for p in baseline["projections"]]

        results.append({
            "name": name,
            "method": "correlacion_como_elasticidad",
            "variable": variable,
            "change_pct": change_pct,
            "correlation_used": round(corr, 2),
            "estimated_effect_pct": round(effect_pct, 2),
            "projections": adjusted,
        })

    return {"baseline": baseline, "scenarios": results}
