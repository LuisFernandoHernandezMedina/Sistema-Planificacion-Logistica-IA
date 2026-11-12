# -*- coding: utf-8 -*-
"""Pruebas del módulo B: Hill Climbing."""

from algoritmos.busqueda_local import hill_climbing
from core.costos import costo_orden_por_posiciones


def test_hill_climbing_valido_y_reproducible(datos_costos):
    matriz = datos_costos["matriz"]
    n = len(matriz) - 2
    primera = hill_climbing(matriz, n_entregas=n, soluciones_iniciales=10,
                            max_iteraciones=200, semilla=42)
    segunda = hill_climbing(matriz, n_entregas=n, soluciones_iniciales=10,
                            max_iteraciones=200, semilla=42)

    assert primera["soluciones_iniciales"] >= 10
    assert len(primera["ejecuciones"]) >= 10
    assert sorted(primera["mejor"]["orden"]) == list(range(n))
    assert primera["mejor"]["costo"] == costo_orden_por_posiciones(
        primera["mejor"]["orden"], matriz)
    assert primera["mejor"] == segunda["mejor"]
    assert primera["ejecuciones"] == segunda["ejecuciones"]


def test_hill_climbing_no_empeora(datos_costos):
    matriz = datos_costos["matriz"]
    resultado = hill_climbing(matriz, soluciones_iniciales=10, semilla=7)
    for ejecucion in resultado["ejecuciones"]:
        assert ejecucion["costo_final"] <= ejecucion["costo_inicial"] + 1e-9
        assert ejecucion["iteraciones"] >= 0


def test_analisis_local(datos_costos):
    matriz = datos_costos["matriz"]
    resultado = hill_climbing(matriz, soluciones_iniciales=10, semilla=42)
    analisis = resultado["analisis"]
    for clave in ("mejor_costo", "costo_promedio", "desviacion_estandar",
                  "optimos_locales_distintos", "corridas_con_meseta",
                  "porcentaje_mesetas", "variabilidad_costo"):
        assert clave in analisis
    assert analisis["mejor_costo"] <= analisis["costo_promedio"] + 1e-9
    assert analisis["costo_promedio"] <= analisis["peor_costo"] + 1e-9


def test_semillas_distintas_generan_inicios_distintos(datos_costos):
    matriz = datos_costos["matriz"]
    a = hill_climbing(matriz, soluciones_iniciales=10, semilla=1)
    b = hill_climbing(matriz, soluciones_iniciales=10, semilla=2)
    inicios_a = [e["costo_inicial"] for e in a["ejecuciones"]]
    inicios_b = [e["costo_inicial"] for e in b["ejecuciones"]]
    assert inicios_a != inicios_b
