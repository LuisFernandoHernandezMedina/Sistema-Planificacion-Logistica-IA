# -*- coding: utf-8 -*-
"""
Módulo C (parte 2): Algoritmo Genético adaptado del Proyecto 5.

Se conserva la lógica del algoritmo genético original:
    - población inicial de permutaciones,
    - selección por torneo,
    - cruzamiento Order Crossover (OX),
    - mutación por intercambio (swap),
    - elitismo.

Adaptaciones al nuevo escenario:
    - la solución es el orden de visita de las entregas,
    - la ruta es abierta: Inicio -> entregas -> Destino final,
    - la aptitud usa la matriz de costos mínimos calculada con A*,
      por lo que respeta obstáculos, costos variables y conectividad.

Los operadores OX y mutación están definidos en este mismo módulo, de modo
que el algoritmo no depende de archivos externos al paquete `algoritmos`.

Contador de evaluaciones:
    Cada llamada a la función objetivo (costo de una permutación) se cuenta
    exactamente una vez. La selección por torneo NO vuelve a evaluar: usa los
    costos ya calculados de la generación (`costos`). Por eso
    evaluaciones = tamano_poblacion * (generaciones + 1), y coincide con el
    número real de llamadas a `costo_orden_por_posiciones`.
"""

from __future__ import annotations

import math
import random
import statistics
import time

from core.costos import costo_orden_por_posiciones


def _costo(orden, matriz, contador_evaluaciones=None):
    if contador_evaluaciones is not None:
        contador_evaluaciones[0] += 1
    return costo_orden_por_posiciones(orden, matriz)


def generar_poblacion(tamano, n_entregas, rng):
    return [rng.sample(range(n_entregas), n_entregas) for _ in range(tamano)]


def seleccion_torneo(poblacion, costos, tamanio_torneo, rng):
    """Torneo: elige `tamanio_torneo` índices al azar y devuelve el mejor.

    Usa los costos ya calculados (`costos[k]` es el costo de `poblacion[k]`),
    por lo que no realiza evaluaciones adicionales de la función objetivo.
    """
    indices = rng.sample(range(len(poblacion)), tamanio_torneo)
    ganador = min(indices, key=lambda k: costos[k])
    return poblacion[ganador][:]


def cruzamiento_ox(padre1, padre2, rng=None):
    """Order Crossover (OX) para permutaciones.

    1. Se eligen dos puntos de corte a <= b.
    2. El segmento [a, b] del padre1 se copia al hijo.
    3. Las posiciones restantes se llenan con los genes del padre2 en orden
       circular a partir de b+1, omitiendo los ya copiados.
    Siempre devuelve una permutación válida (sin repetidos ni faltantes).
    """
    rng = rng or random
    n = len(padre1)
    a, b = sorted(rng.sample(range(n), 2))
    hijo = [None] * n
    hijo[a:b + 1] = padre1[a:b + 1]
    orden_padre2 = padre2[b + 1:] + padre2[:b + 1]
    idx = 0
    for i in range(n):
        if hijo[i] is None:
            while orden_padre2[idx] in hijo:
                idx += 1
            hijo[i] = orden_padre2[idx]
            idx += 1
    return hijo


def mutar(orden, prob_mutacion, rng=None):
    """Mutación swap: con probabilidad `prob_mutacion` intercambia dos genes."""
    rng = rng or random
    orden = orden[:]
    if len(orden) >= 2 and rng.random() < prob_mutacion:
        i, j = rng.sample(range(len(orden)), 2)
        orden[i], orden[j] = orden[j], orden[i]
    return orden


def algoritmo_genetico(matriz, n_entregas=None, tamano_poblacion=60,
                       generaciones=150, prob_mutacion=0.15, prob_cruce=0.9,
                       tamanio_torneo=3, elitismo=True, semilla=42):
    """Ejecuta una corrida del algoritmo genético y devuelve métricas."""
    if n_entregas is None:
        n_entregas = len(matriz) - 2
    if n_entregas <= 0:
        raise ValueError("Se requiere al menos una entrega.")
    if n_entregas == 1:
        orden = [0]
        costo = costo_orden_por_posiciones(orden, matriz)
        return {
            "metodo": "Algoritmo genético",
            "mejor_orden": orden,
            "mejor_costo": round(costo, 4),
            "costo_inicial": round(costo, 4),
            "generaciones_ejecutadas": 0,
            "evaluaciones": 1,
            "historial_mejor": [round(costo, 4)],
            "tiempo_ms": 0.0,
            "parametros": {},
        }

    rng = random.Random(semilla)
    inicio = time.perf_counter()
    evaluaciones = [0]
    poblacion = generar_poblacion(int(tamano_poblacion), n_entregas, rng)

    mejor_global = None
    mejor_costo = math.inf
    historial = []
    generacion_ultima_mejora = 0
    generaciones_ejecutadas = 0

    for generacion in range(int(generaciones) + 1):
        generaciones_ejecutadas = generacion
        costos = [_costo(ind, matriz, evaluaciones) for ind in poblacion]
        idx_mejor = min(range(len(poblacion)), key=lambda k: costos[k])

        if costos[idx_mejor] < mejor_costo - 1e-9:
            mejor_costo = costos[idx_mejor]
            mejor_global = poblacion[idx_mejor][:]
            generacion_ultima_mejora = generacion

        historial.append(round(mejor_costo, 4))

        if generacion == int(generaciones):
            break

        nueva = []
        if elitismo:
            nueva.append(mejor_global[:])

        while len(nueva) < int(tamano_poblacion):
            padre1 = seleccion_torneo(poblacion, costos, int(tamanio_torneo), rng)
            padre2 = seleccion_torneo(poblacion, costos, int(tamanio_torneo), rng)
            if n_entregas >= 2 and rng.random() < prob_cruce:
                hijo = cruzamiento_ox(padre1, padre2, rng=rng)
            else:
                hijo = padre1[:]
            hijo = mutar(hijo, prob_mutacion, rng=rng)
            nueva.append(hijo)

        poblacion = nueva

    sin_mejora = generaciones_ejecutadas - generacion_ultima_mejora
    return {
        "metodo": "Algoritmo genético (OX + swap + torneo + elitismo)",
        "mejor_orden": mejor_global,
        "mejor_costo": round(mejor_costo, 4),
        "costo_inicial": historial[0] if historial else None,
        "costo_final_poblacion": round(min(costos), 4),
        "generaciones_ejecutadas": generaciones_ejecutadas,
        "evaluaciones": evaluaciones[0],
        "historial_mejor": historial,
        "generaciones_sin_mejora": sin_mejora,
        "posible_convergencia_prematura": sin_mejora >= max(20, generaciones // 3),
        "parametros": {
            "tamano_poblacion": int(tamano_poblacion),
            "generaciones": int(generaciones),
            "prob_mutacion": float(prob_mutacion),
            "prob_cruce": float(prob_cruce),
            "tamanio_torneo": int(tamanio_torneo),
            "elitismo": bool(elitismo),
        },
        "tiempo_ms": round((time.perf_counter() - inicio) * 1000.0, 3),
    }


def ejecutar_repeticiones(matriz, repeticiones=20, semilla_base=42, **parametros):
    """Ejecuta varias corridas con semillas reproducibles y resume resultados."""
    corridas = []
    for i in range(int(repeticiones)):
        corrida = algoritmo_genetico(
            matriz, semilla=semilla_base + i, **parametros)
        corrida["semilla"] = semilla_base + i
        corrida["corrida"] = i + 1
        corridas.append(corrida)

    costos = [c["mejor_costo"] for c in corridas]
    promedio = sum(costos) / len(costos)
    varianza = sum((c - promedio) ** 2 for c in costos) / len(costos)
    return {
        "metodo": "Algoritmo genético",
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
