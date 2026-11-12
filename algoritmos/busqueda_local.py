# -*- coding: utf-8 -*-
"""
Módulo B: búsqueda local (Hill Climbing) para ordenar entregas.

Representación de la solución candidata:
    una permutación de posiciones de entregas (0 .. m-1).

Función de evaluación:
    costo de la ruta Inicio -> entregas en ese orden -> Destino, usando la
    matriz de costos mínimos calculada con A* (obstáculos y costos variables).

Vecindad:
    intercambio de dos entregas (swap) en todas las posiciones posibles.

Selección:
    se elige la mejor solución vecina (mejor mejora).

Criterio de terminación:
    detenerse cuando ningún vecino mejora estrictamente el costo actual
    (óptimo local) o al alcanzar `max_iteraciones`.
"""

from __future__ import annotations

import math
import random
import statistics
import time

from core.costos import costo_orden_por_posiciones


def _evaluar(orden, matriz, evaluaciones):
    evaluaciones[0] += 1
    return costo_orden_por_posiciones(orden, matriz)


def _vecinos(orden):
    n = len(orden)
    for i in range(n - 1):
        for j in range(i + 1, n):
            vecino = list(orden)
            vecino[i], vecino[j] = vecino[j], vecino[i]
            yield tuple(vecino)


def hill_climbing(matriz, n_entregas=None, soluciones_iniciales=10,
                  max_iteraciones=200, semilla=42):
    """
    Ejecuta Hill Climbing desde varias soluciones iniciales.

    Devuelve las métricas por ejecución, la mejor solución y un análisis
    de óptimos locales, mesetas y variabilidad.
    """
    if n_entregas is None:
        n_entregas = len(matriz) - 2
    if n_entregas <= 0:
        raise ValueError("Se requiere al menos una entrega.")
    soluciones_iniciales = max(10, int(soluciones_iniciales))
    rng = random.Random(semilla)

    inicio_global = time.perf_counter()
    evaluaciones = [0]
    ejecuciones = []
    historial_mejor_global = []
    mejor_global = None

    for corrida in range(soluciones_iniciales):
        orden = tuple(rng.sample(range(n_entregas), n_entregas))
        costo_actual = _evaluar(orden, matriz, evaluaciones)
        costo_inicial = costo_actual
        historial = [costo_actual]
        iteraciones = 0
        vecinos_empatados = 0

        while iteraciones < max_iteraciones:
            mejor_vecino = None
            mejor_costo_vecino = math.inf
            empatados = 0

            for vecino in _vecinos(orden):
                costo_vecino = _evaluar(vecino, matriz, evaluaciones)
                if costo_vecino < mejor_costo_vecino - 1e-9:
                    mejor_costo_vecino = costo_vecino
                    mejor_vecino = vecino
                    empatados = 0
                elif abs(costo_vecino - mejor_costo_vecino) <= 1e-9:
                    empatados += 1

            if mejor_vecino is None or mejor_costo_vecino >= costo_actual - 1e-9:
                vecinos_empatados = sum(
                    1 for vecino in _vecinos(orden)
                    if abs(_evaluar(vecino, matriz, evaluaciones) - costo_actual)
                    <= 1e-9)
                break

            orden = mejor_vecino
            costo_actual = mejor_costo_vecino
            iteraciones += 1
            historial.append(costo_actual)

            if mejor_global is None or costo_actual < mejor_global["costo"]:
                mejor_global = {
                    "orden": list(orden),
                    "costo": costo_actual,
                    "corrida": corrida,
                }

        if mejor_global is None or costo_actual < mejor_global["costo"] - 1e-9:
            mejor_global = {
                "orden": list(orden),
                "costo": costo_actual,
                "corrida": corrida,
            }

        ejecuciones.append({
            "corrida": corrida + 1,
            "orden": list(orden),
            "costo_inicial": round(costo_inicial, 4),
            "costo_final": round(costo_actual, 4),
            "mejora": round(costo_inicial - costo_actual, 4),
            "iteraciones": iteraciones,
            "vecinos_meseta": vecinos_empatados,
            "es_meseta": vecinos_empatados > 0,
        })
        historial_mejor_global.append(round(mejor_global["costo"], 4))

    costos = [e["costo_final"] for e in ejecuciones]
    ordenes_unicos = {tuple(e["orden"]) for e in ejecuciones}
    mesetas = [e for e in ejecuciones if e["es_meseta"]]

    analisis = {
        "mejor_costo": round(min(costos), 4),
        "peor_costo": round(max(costos), 4),
        "costo_promedio": round(statistics.mean(costos), 4),
        "desviacion_estandar": round(
            statistics.pstdev(costos) if len(costos) > 1 else 0.0, 4),
        "optimos_locales_distintos": len(ordenes_unicos),
        "corridas_con_meseta": len(mesetas),
        "porcentaje_mesetas": round(100.0 * len(mesetas) / len(ejecuciones), 2),
        "variabilidad_costo": round(max(costos) - min(costos), 4),
    }

    return {
        "metodo": "Hill Climbing (mejor mejora, vecindad swap)",
        "soluciones_iniciales": soluciones_iniciales,
        "max_iteraciones": max_iteraciones,
        "evaluaciones": evaluaciones[0],
        "mejor": {
            "orden": mejor_global["orden"] if mejor_global else [],
            "costo": round(mejor_global["costo"], 4) if mejor_global else None,
        },
        "ejecuciones": ejecuciones,
        "analisis": analisis,
        "historial_mejor_global": historial_mejor_global,
        "tiempo_total_ms": round((time.perf_counter() - inicio_global) * 1000.0, 3),
    }
