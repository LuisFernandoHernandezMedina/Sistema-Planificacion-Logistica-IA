# -*- coding: utf-8 -*-
"""
Costos de rutas compartidos por búsqueda local, metaheurísticas e integración.

La distancia entre dos puntos NO es euclidiana: se calcula con A* sobre la
cuadrícula, por lo que los obstáculos y los costos variables influyen en
todos los módulos.
"""

from __future__ import annotations

import math


def construir_matriz_costos(escenario, funcion_ruta=None):
    """
    Construye la matriz de costos mínimos entre Inicio, entregas y Destino.

    Orden de los nodos: [Inicio, Entrega 1, ..., Entrega n, Destino].
    Devuelve un diccionario con:
      - puntos: nombres de los nodos,
      - coordenadas: lista de (x, y),
      - matriz: matriz n x n de costos,
      - caminos: diccionario (i, j) -> lista de celdas de la ruta,
      - inalcanzables: lista de pares sin camino.
    """
    if funcion_ruta is None:
        from algoritmos.busqueda_heuristica import a_estrella
        funcion_ruta = a_estrella

    puntos = escenario.puntos_interes()
    nombres = [p[0] for p in puntos]
    coordenadas = [(p[1], p[2]) for p in puntos]
    n = len(coordenadas)
    matriz = [[math.inf for _ in range(n)] for _ in range(n)]
    caminos = {}
    inalcanzables = []

    for i in range(n):
        matriz[i][i] = 0.0
        for j in range(i + 1, n):
            resultado = funcion_ruta(escenario.mapa, coordenadas[i], coordenadas[j])
            if resultado.get("encontrado"):
                costo = float(resultado["costo"])
                matriz[i][j] = costo
                matriz[j][i] = costo
                caminos[(i, j)] = resultado["camino"]
                caminos[(j, i)] = list(reversed(resultado["camino"]))
            else:
                inalcanzables.append([i, j])

    return {
        "puntos": nombres,
        "coordenadas": coordenadas,
        "matriz": matriz,
        "caminos": caminos,
        "inalcanzables": inalcanzables,
    }


def costo_orden(orden, matriz, idx_inicio=0, idx_destino=None):
    """
    Costo de visitar `orden` (índices de entregas) desde Inicio hasta Destino.

    `orden` contiene índices de la matriz, no posiciones dentro de la lista.
    Si no se especifica idx_destino se usa el último nodo de la matriz.
    """
    if idx_destino is None:
        idx_destino = len(matriz) - 1
    if orden is None:
        return math.inf
    if len(orden) == 0:
        return float(matriz[idx_inicio][idx_destino])

    total = float(matriz[idx_inicio][orden[0]])
    for i in range(len(orden) - 1):
        total += float(matriz[orden[i]][orden[i + 1]])
    total += float(matriz[orden[-1]][idx_destino])
    return total


def costo_orden_por_posiciones(orden_posiciones, matriz, idx_inicio=0,
                               idx_destino=None):
    """
    Igual que costo_orden, pero `orden_posiciones` usa 0..n-2 para las
    entregas. Se usa en la interfaz y en los experimentos.
    """
    indices = [i + 1 for i in orden_posiciones]
    return costo_orden(indices, matriz, idx_inicio, idx_destino)


def ruta_coordenadas(orden, datos_costos):
    """Convierte un orden de entregas en la lista completa de celdas."""
    coords = datos_costos["coordenadas"]
    caminos = datos_costos["caminos"]
    n = len(coords)
    secuencia = [0] + list(orden) + [n - 1]
    ruta = [coords[secuencia[0]]]
    for a, b in zip(secuencia, secuencia[1:]):
        tramo = caminos.get((a, b))
        if tramo:
            ruta.extend(tramo[1:])
        else:
            ruta.append(coords[b])
    return ruta


def nombres_orden(orden, datos_costos):
    """Devuelve la ruta completa como nombres legibles."""
    nombres = datos_costos["puntos"]
    n = len(nombres)
    return [nombres[0]] + [nombres[i] for i in orden] + [nombres[n - 1]]
