# -*- coding: utf-8 -*-
"""
Módulo A: búsqueda heurística sobre la cuadrícula.

Implementa manualmente:
  - Greedy Best-First Search (prioridad h(n)),
  - A* (prioridad f(n) = g(n) + h(n)).

Heurística utilizada:
    h(n) = distancia Manhattan(n, destino) * costo_minimo_de_la_cuadrícula

Es admisible porque cada movimiento cambia la distancia Manhattan en 1 y
cada paso cuesta al menos `costo_minimo`. Por tanto h(n) nunca sobreestima
el costo real restante. También es consistente: h(n) - h(n') <= costo(n, n').

A* garantiza optimalidad con costos positivos y una heurística admisible.
Greedy no la garantiza porque ignora g(n).
"""

from __future__ import annotations

import heapq
import itertools
import math
import time


def heuristica_manhattan(a, b, costo_minimo=1.0):
    """Distancia Manhattan multiplicada por el menor costo de celda."""
    return (abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))) * costo_minimo


def _resultado(camino, costo, expandidos, inicio_tiempo, encontrado,
               mensaje, criterio):
    return {
        "encontrado": bool(encontrado),
        "camino": camino,
        "costo": float(costo) if math.isfinite(costo) else None,
        "longitud": max(0, len(camino) - 1) if camino else 0,
        "nodos_expandidos": int(expandidos),
        "tiempo_ms": round((time.perf_counter() - inicio_tiempo) * 1000.0, 3),
        "mensaje": mensaje,
        "criterio": criterio,
    }


def a_estrella(mapa, inicio, destino):
    """A* con f(n) = g(n) + h(n). Devuelve ruta, costo y métricas."""
    inicio_tiempo = time.perf_counter()
    inicio = (int(inicio[0]), int(inicio[1]))
    destino = (int(destino[0]), int(destino[1]))

    if not mapa.es_transitable(*inicio):
        return _resultado([], math.inf, 0, inicio_tiempo, False,
                          "El inicio no es transitable.", "f(n)=g(n)+h(n)")
    if not mapa.es_transitable(*destino):
        return _resultado([], math.inf, 0, inicio_tiempo, False,
                          "El destino no es transitable.", "f(n)=g(n)+h(n)")
    if inicio == destino:
        return _resultado([inicio], 0.0, 1, inicio_tiempo, True,
                          "El inicio coincide con el destino.", "f(n)=g(n)+h(n)")

    costo_minimo = mapa.costo_minimo()
    contador = itertools.count()
    abiertos = []
    heapq.heappush(abiertos, (0.0, next(contador), inicio))
    g = {inicio: 0.0}
    padres = {inicio: None}
    cerrados = set()
    expandidos = 0

    while abiertos:
        _, _, actual = heapq.heappop(abiertos)
        if actual in cerrados:
            continue
        cerrados.add(actual)
        expandidos += 1

        if actual == destino:
            camino = _reconstruir(padres, destino)
            return _resultado(camino, g[destino], expandidos, inicio_tiempo,
                              True, "Ruta óptima encontrada con A*.",
                              "f(n)=g(n)+h(n)")

        for vecino in mapa.vecinos(*actual):
            if vecino in cerrados:
                continue
            nuevo_g = g[actual] + mapa.costo(*vecino)
            if nuevo_g < g.get(vecino, math.inf):
                g[vecino] = nuevo_g
                padres[vecino] = actual
                h = heuristica_manhattan(vecino, destino, costo_minimo)
                heapq.heappush(abiertos, (nuevo_g + h, next(contador), vecino))

    return _resultado([], math.inf, expandidos, inicio_tiempo, False,
                      "No existe una ruta transitable entre inicio y destino.",
                      "f(n)=g(n)+h(n)")


def greedy_best_first(mapa, inicio, destino):
    """Greedy Best-First: prioridad únicamente h(n)."""
    inicio_tiempo = time.perf_counter()
    inicio = (int(inicio[0]), int(inicio[1]))
    destino = (int(destino[0]), int(destino[1]))

    if not mapa.es_transitable(*inicio):
        return _resultado([], math.inf, 0, inicio_tiempo, False,
                          "El inicio no es transitable.", "h(n)")
    if not mapa.es_transitable(*destino):
        return _resultado([], math.inf, 0, inicio_tiempo, False,
                          "El destino no es transitable.", "h(n)")
    if inicio == destino:
        return _resultado([inicio], 0.0, 1, inicio_tiempo, True,
                          "El inicio coincide con el destino.", "h(n)")

    costo_minimo = mapa.costo_minimo()
    contador = itertools.count()
    abiertos = []
    heapq.heappush(
        abiertos,
        (heuristica_manhattan(inicio, destino, costo_minimo), next(contador), inicio))
    padres = {inicio: None}
    costo_acumulado = {inicio: 0.0}
    visitados = set()
    expandidos = 0

    while abiertos:
        _, _, actual = heapq.heappop(abiertos)
        if actual in visitados:
            continue
        visitados.add(actual)
        expandidos += 1

        if actual == destino:
            camino = _reconstruir(padres, destino)
            return _resultado(camino, costo_acumulado[destino], expandidos,
                              inicio_tiempo, True,
                              "Ruta encontrada con Greedy (no garantiza óptimo).",
                              "h(n)")

        for vecino in mapa.vecinos(*actual):
            if vecino in visitados:
                continue
            if vecino not in padres:
                padres[vecino] = actual
                costo_acumulado[vecino] = costo_acumulado[actual] + mapa.costo(*vecino)
                heapq.heappush(
                    abiertos,
                    (heuristica_manhattan(vecino, destino, costo_minimo),
                     next(contador), vecino))

    return _resultado([], math.inf, expandidos, inicio_tiempo, False,
                      "No existe una ruta transitable entre inicio y destino.",
                      "h(n)")


def _reconstruir(padres, destino):
    camino = []
    actual = destino
    while actual is not None:
        camino.append(actual)
        actual = padres[actual]
    camino.reverse()
    return camino


def comparar_greedy_a_estrella(mapa, inicio, destino):
    """Ejecuta ambos algoritmos y devuelve una comparación estructurada."""
    greedy = greedy_best_first(mapa, inicio, destino)
    astar = a_estrella(mapa, inicio, destino)

    diferencia_costo = None
    if greedy["encontrado"] and astar["encontrado"]:
        diferencia_costo = round(astar["costo"] - greedy["costo"], 4)

    return {
        "inicio": list(inicio),
        "destino": list(destino),
        "greedy": greedy,
        "a_estrella": astar,
        "diferencia_costo_a_menos_greedy": diferencia_costo,
        "astar_es_optimo": bool(astar["encontrado"]),
    }
