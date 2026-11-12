# -*- coding: utf-8 -*-
"""Pruebas del módulo D: teoría de juegos."""

from algoritmos.teoria_juegos import (
    ESTRATEGIAS_COMPETIDOR,
    ESTRATEGIAS_EMPRESA,
    analizar_juego,
    construir_matriz_pagos,
    dominancia,
    equilibrios_nash,
    mejores_respuestas,
)


def test_matriz_tres_por_tres(escenario):
    juego = construir_matriz_pagos(escenario, 34.0)
    assert len(juego["matriz"]) == 3
    assert all(len(fila) == 3 for fila in juego["matriz"])
    for fila in juego["matriz"]:
        for celda in fila:
            assert "empresa" in celda
            assert "competidor" in celda
            assert celda["costo_ruta"] > 0


def test_mejores_respuestas_coherentes(escenario):
    juego = analizar_juego(escenario, 34.0)
    matriz = juego["matriz"]
    respuestas = juego["mejores_respuestas"]
    for item in respuestas["empresa"]:
        j = ESTRATEGIAS_COMPETIDOR.index(item["competidor"])
        valores = [matriz[i][j]["empresa"] for i in range(3)]
        assert item["pago_maximo"] == max(valores)
    for item in respuestas["competidor"]:
        i = ESTRATEGIAS_EMPRESA.index(item["empresa"])
        valores = [matriz[i][j]["competidor"] for j in range(3)]
        assert item["pago_maximo"] == max(valores)


def test_equilibrios_nash_son_mejores_respuestas(escenario):
    juego = analizar_juego(escenario, 34.0)
    matriz = juego["matriz"]
    assert juego["equilibrios_nash"], "El escenario base debe tener al menos un Nash."
    for equilibrio in juego["equilibrios_nash"]:
        i, j = equilibrio["fila"], equilibrio["columna"]
        assert matriz[i][j]["empresa"] == max(
            matriz[k][j]["empresa"] for k in range(3))
        assert matriz[i][j]["competidor"] == max(
            matriz[i][k]["competidor"] for k in range(3))


def test_dominancia_del_competidor(escenario):
    juego = analizar_juego(escenario, 34.0)
    dominancia_comp = juego["dominancia"]["competidor"]
    assert dominancia_comp["dominantes"]
    assert any(d["estrategia"] == "Bloqueo de ruta"
               for d in dominancia_comp["dominantes"])


def test_juego_sin_nash_puro():
    # Matriz tipo piedra-papel-tijera: no tiene equilibrio de Nash puro.
    valores = [[0, 1, -1], [-1, 0, 1], [1, -1, 0]]
    matriz = [[{"empresa": valores[i][j],
                "competidor": -valores[i][j],
                "costo_ruta": 1.0,
                "penalizacion_recursos": 0.0,
                "factor_costo": 1.0}
               for j in range(3)] for i in range(3)]
    assert equilibrios_nash(matriz) == []
    assert dominancia(matriz)["empresa"]["dominantes"] == []
    respuestas = mejores_respuestas(matriz)
    assert len(respuestas["empresa"]) == 3


def test_nash_verificado_por_desviaciones_unilaterales(escenario):
    """Cada Nash reportado debe resistir toda desviación unilateral."""
    juego = analizar_juego(escenario, 34.0)
    matriz = juego["matriz"]
    for eq in juego["equilibrios_nash"]:
        i, j = eq["fila"], eq["columna"]
        assert all(matriz[k][j]["empresa"] <= matriz[i][j]["empresa"] + 1e-9
                   for k in range(3))
        assert all(matriz[i][k]["competidor"] <= matriz[i][j]["competidor"] + 1e-9
                   for k in range(3))
        assert "caracterizacion" in eq


def test_nash_por_fuerza_bruta_coincide(escenario):
    """Las celdas que son mejor respuesta de ambos == equilibrios reportados."""
    juego = analizar_juego(escenario, 34.0)
    m = juego["matriz"]
    esperados = {(i, j) for i in range(3) for j in range(3)
                 if m[i][j]["empresa"] == max(m[k][j]["empresa"] for k in range(3))
                 and m[i][j]["competidor"] == max(m[i][k]["competidor"] for k in range(3))}
    obtenidos = {(e["fila"], e["columna"]) for e in juego["equilibrios_nash"]}
    assert obtenidos == esperados


def test_dominante_exige_dominar_a_todas():
    """Dominar a una sola estrategia no convierte a otra en 'dominante'."""
    # Para la empresa: A domina a C pero no a B -> ninguna es dominante.
    pagos = [[3, 1], [1, 3], [0, 0]]
    matriz = [[{"empresa": pagos[i][j], "competidor": 0} for j in range(2)]
              for i in range(3)]
    dom = dominancia(matriz)
    assert dom["empresa"]["dominantes_sobre_todas"] == []
    # Pero sí se registra la dominancia por pares (A y B dominan a C).
    assert any(d["estrategia"] == "Ruta rápida" and d["domina_a"] == "Reserva preventiva"
               for d in dom["empresa"]["dominantes"])
