# -*- coding: utf-8 -*-
"""Pruebas del módulo C: recocido simulado y algoritmo genético."""

from algoritmos.algoritmo_genetico import algoritmo_genetico
from algoritmos.recocido_simulado import recocido_simulado
from core.costos import costo_orden_por_posiciones


def test_recocido_reproducible(datos_costos):
    matriz = datos_costos["matriz"]
    n = len(matriz) - 2
    a = recocido_simulado(matriz, n_entregas=n,
                          iteraciones_por_temperatura=20, semilla=42)
    b = recocido_simulado(matriz, n_entregas=n,
                          iteraciones_por_temperatura=20, semilla=42)
    assert a["mejor_orden"] == b["mejor_orden"]
    assert a["mejor_costo"] == b["mejor_costo"]
    assert a["historial_mejor"] == b["historial_mejor"]
    assert sorted(a["mejor_orden"]) == list(range(n))
    assert a["mejor_costo"] == costo_orden_por_posiciones(
        a["mejor_orden"], matriz)


def test_recocido_parametros(datos_costos):
    matriz = datos_costos["matriz"]
    resultado = recocido_simulado(
        matriz, temperatura_inicial=10.0, temperatura_final=0.1,
        factor_enfriamiento=0.9, iteraciones_por_temperatura=5, semilla=3)
    assert resultado["aceptaciones"] + resultado["rechazos"] == \
        resultado["iteraciones"]
    assert resultado["temperatura_final_alcanzada"] <= 0.1 + 1e-9


def test_genetico_reproducible(datos_costos):
    matriz = datos_costos["matriz"]
    n = len(matriz) - 2
    parametros = dict(tamano_poblacion=20, generaciones=12,
                      prob_mutacion=0.15, prob_cruce=0.9,
                      tamanio_torneo=3, semilla=42)
    a = algoritmo_genetico(matriz, n_entregas=n, **parametros)
    b = algoritmo_genetico(matriz, n_entregas=n, **parametros)
    assert a["mejor_orden"] == b["mejor_orden"]
    assert a["mejor_costo"] == b["mejor_costo"]
    assert a["historial_mejor"] == b["historial_mejor"]
    assert sorted(a["mejor_orden"]) == list(range(n))
    assert a["mejor_costo"] == costo_orden_por_posiciones(
        a["mejor_orden"], matriz)


def test_genetico_historial_y_evaluaciones(datos_costos):
    matriz = datos_costos["matriz"]
    resultado = algoritmo_genetico(
        matriz, tamano_poblacion=20, generaciones=15, semilla=5)
    assert len(resultado["historial_mejor"]) == 16
    assert resultado["evaluaciones"] > 0
    assert resultado["generaciones_ejecutadas"] == 15
    assert resultado["historial_mejor"][-1] <= resultado["historial_mejor"][0]


def test_genetico_contador_coincide_con_llamadas_reales(datos_costos, monkeypatch):
    """El contador debe igualar las llamadas reales a la función objetivo."""
    import algoritmos.algoritmo_genetico as modulo
    matriz = datos_costos["matriz"]
    llamadas = [0]
    original = modulo.costo_orden_por_posiciones

    def contado(orden, m):
        llamadas[0] += 1
        return original(orden, m)

    monkeypatch.setattr(modulo, "costo_orden_por_posiciones", contado)
    resultado = modulo.algoritmo_genetico(
        matriz, tamano_poblacion=20, generaciones=15, semilla=5)
    assert resultado["evaluaciones"] == llamadas[0]
    assert resultado["evaluaciones"] == 20 * (15 + 1)


def test_operadores_geneticos_conservan_permutacion():
    import random
    from algoritmos.algoritmo_genetico import cruzamiento_ox, mutar
    rng = random.Random(1)
    for _ in range(200):
        p1 = rng.sample(range(7), 7)
        p2 = rng.sample(range(7), 7)
        assert sorted(cruzamiento_ox(p1, p2, rng=rng)) == list(range(7))
        assert sorted(mutar(p1, 1.0, rng=rng)) == list(range(7))
