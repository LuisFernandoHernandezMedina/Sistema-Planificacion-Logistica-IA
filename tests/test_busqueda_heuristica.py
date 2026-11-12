# -*- coding: utf-8 -*-
"""Pruebas del módulo A: Greedy Best-First y A*."""

from algoritmos.busqueda_heuristica import (
    a_estrella,
    comparar_greedy_a_estrella,
    greedy_best_first,
    heuristica_manhattan,
)
from core.mapa import Mapa


def _camino_valido(mapa, camino, inicio, destino):
    assert camino[0] == inicio
    assert camino[-1] == destino
    for a, b in zip(camino, camino[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
        assert mapa.es_transitable(*b)


def test_a_estrella_camino_simple():
    mapa = Mapa(filas=3, columnas=3,
                costos=[[1, 1, 1], [1, 1, 1], [1, 1, 1]])
    resultado = a_estrella(mapa, (0, 0), (2, 2))
    assert resultado["encontrado"]
    assert resultado["costo"] == 4
    assert resultado["longitud"] == 4
    _camino_valido(mapa, resultado["camino"], (0, 0), (2, 2))


def test_a_estrella_evita_costos_altos():
    mapa = Mapa(filas=2, columnas=5,
                costos=[[1, 5, 1, 5, 1], [1, 1, 1, 1, 1]])
    resultado = a_estrella(mapa, (0, 0), (4, 0))
    assert resultado["encontrado"]
    assert resultado["costo"] == 6
    _camino_valido(mapa, resultado["camino"], (0, 0), (4, 0))


def test_greedy_puede_ser_peor_que_astar(escenario):
    comparacion = comparar_greedy_a_estrella(
        escenario.mapa, escenario.inicio, escenario.destino)
    assert comparacion["a_estrella"]["encontrado"]
    assert comparacion["greedy"]["encontrado"]
    assert comparacion["a_estrella"]["costo"] <= comparacion["greedy"]["costo"]
    assert comparacion["diferencia_costo_a_menos_greedy"] is not None


def test_sin_solucion(mapa_sin_solucion):
    for funcion in (a_estrella, greedy_best_first):
        resultado = funcion(mapa_sin_solucion, (0, 0), (4, 4))
        assert resultado["encontrado"] is False
        assert resultado["camino"] == []
        assert resultado["costo"] is None


def test_obstaculos_en_camino(escenario):
    resultado = a_estrella(escenario.mapa, escenario.inicio, escenario.destino)
    for x, y in resultado["camino"]:
        assert escenario.mapa.es_transitable(x, y)


def test_heuristica_admisible(escenario):
    resultado = a_estrella(escenario.mapa, escenario.inicio, escenario.destino)
    h = heuristica_manhattan(
        escenario.inicio, escenario.destino, escenario.mapa.costo_minimo())
    assert h <= resultado["costo"] + 1e-9


def test_inicio_o_destino_obstaculo(mapa_sin_solucion):
    resultado = a_estrella(mapa_sin_solucion, (2, 0), (4, 4))
    assert resultado["encontrado"] is False
