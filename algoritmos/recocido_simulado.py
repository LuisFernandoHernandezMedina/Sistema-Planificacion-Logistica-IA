# -*- coding: utf-8 -*-
"""
Módulo C (parte 1): Recocido Simulado.

Regla de aceptación:
    si el vecino mejora (delta <= 0) se acepta siempre;
    si empeora (delta > 0) se acepta con probabilidad
        P = exp(-delta / T)
    donde T es la temperatura actual.

Enfriamiento geométrico:
    T_{k+1} = alpha * T_k, con 0 < alpha < 1.

Terminación:
    cuando T <= temperatura_final o se alcanza el máximo de iteraciones.

La solución candidata es el orden de visita de las entregas y la evaluación
usa la matriz de costos mínimos entre puntos (A* sobre la cuadrícula).
"""

from __future__ import annotations

import math
import random
import time

from core.costos import costo_orden_por_posiciones


def recocido_simulado(matriz, n_entregas=None, temperatura_inicial=50.0,
                      temperatura_final=0.01, factor_enfriamiento=0.97,
                      iteraciones_por_temperatura=40, max_iteraciones=100000,
                      semilla=42):
    """Ejecuta una corrida de recocido simulado y devuelve sus métricas."""
    if n_entregas is None:
        n_entregas = len(matriz) - 2
    if n_entregas <= 0:
        raise ValueError("Se requiere al menos una entrega.")
    if factor_enfriamiento <= 0 or factor_enfriamiento >= 1:
        raise ValueError("El factor de enfriamiento debe estar entre 0 y 1.")
    if temperatura_inicial <= 0 or temperatura_final <= 0:
        raise ValueError("Las temperaturas deben ser positivas.")

    rng = random.Random(semilla)
    inicio = time.perf_counter()

    orden_actual = list(rng.sample(range(n_entregas), n_entregas))
    costo_actual = costo_orden_por_posiciones(orden_actual, matriz)
    mejor_orden = orden_actual[:]
    mejor_costo = costo_actual
    historial_mejor = [mejor_costo]
    historial_actual = [costo_actual]

    temperatura = float(temperatura_inicial)
    iteraciones = 0
    evaluaciones = 1
    aceptaciones = 0
    rechazos = 0
    temp_por_iteracion = [temperatura]

    while temperatura > temperatura_final and iteraciones < max_iteraciones:
        for _ in range(int(iteraciones_por_temperatura)):
            if n_entregas < 2:
                break
            i, j = rng.sample(range(n_entregas), 2)
            vecino = orden_actual[:]
            vecino[i], vecino[j] = vecino[j], vecino[i]
            costo_vecino = costo_orden_por_posiciones(vecino, matriz)
            evaluaciones += 1
            delta = costo_vecino - costo_actual

            if delta <= 0 or rng.random() < math.exp(-delta / temperatura):
                orden_actual = vecino
                costo_actual = costo_vecino
                aceptaciones += 1
                if costo_actual < mejor_costo:
                    mejor_costo = costo_actual
                    mejor_orden = orden_actual[:]
            else:
                rechazos += 1

            iteraciones += 1
            historial_mejor.append(mejor_costo)
            historial_actual.append(costo_actual)
            temp_por_iteracion.append(temperatura)
            if iteraciones >= max_iteraciones:
                break

        temperatura *= factor_enfriamiento

    return {
        "metodo": "Recocido simulado",
        "mejor_orden": mejor_orden,
        "mejor_costo": round(mejor_costo, 4),
        "costo_inicial": round(historial_actual[0], 4),
        "costo_final": round(costo_actual, 4),
        "iteraciones": iteraciones,
        "evaluaciones": evaluaciones,
        "aceptaciones": aceptaciones,
        "rechazos": rechazos,
        "temperatura_inicial": float(temperatura_inicial),
        "temperatura_final_alcanzada": round(temperatura, 6),
        "factor_enfriamiento": float(factor_enfriamiento),
        "iteraciones_por_temperatura": int(iteraciones_por_temperatura),
        "historial_mejor": [round(v, 4) for v in historial_mejor],
        "historial_actual": [round(v, 4) for v in historial_actual],
        "temperaturas": [round(v, 6) for v in temp_por_iteracion],
        "tiempo_ms": round((time.perf_counter() - inicio) * 1000.0, 3),
    }


def ejecutar_repeticiones(matriz, repeticiones=20, semilla_base=42, **parametros):
    """Ejecuta varias corridas con semillas reproducibles y resume resultados."""
    corridas = []
    for i in range(int(repeticiones)):
        corrida = recocido_simulado(
            matriz, semilla=semilla_base + i, **parametros)
        corrida["semilla"] = semilla_base + i
        corrida["corrida"] = i + 1
        corridas.append(corrida)

    costos = [c["mejor_costo"] for c in corridas]
    promedio = sum(costos) / len(costos)
    varianza = sum((c - promedio) ** 2 for c in costos) / len(costos)
    return {
        "metodo": "Recocido simulado",
        "repeticiones": len(corridas),
        "mejor_costo": round(min(costos), 4),
        "costo_promedio": round(promedio, 4),
        "desviacion_estandar": round(math.sqrt(varianza), 4),
        "peor_costo": round(max(costos), 4),
        "evaluaciones_promedio": round(
            sum(c["evaluaciones"] for c in corridas) / len(corridas), 1),
        "tiempo_promedio_ms": round(
            sum(c["tiempo_ms"] for c in corridas) / len(corridas), 3),
        "corridas": corridas,
    }
