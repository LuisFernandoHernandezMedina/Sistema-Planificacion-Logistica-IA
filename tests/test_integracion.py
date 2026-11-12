# -*- coding: utf-8 -*-
"""Pruebas de integración: los cinco módulos comparten el escenario."""

from core.integracion import cargar_parametros, ejecutar_planificacion


def _parametros_rapidos():
    parametros = cargar_parametros()
    parametros["busqueda_local"]["soluciones_iniciales"] = 10
    parametros["busqueda_local"]["max_iteraciones"] = 100
    parametros["recocido_simulado"]["iteraciones_por_temperatura"] = 8
    parametros["algoritmo_genetico"]["tamano_poblacion"] = 20
    parametros["algoritmo_genetico"]["generaciones"] = 20
    return parametros


def test_pipeline_completo(escenario):
    resultado = ejecutar_planificacion(escenario, _parametros_rapidos())
    for clave in ("escenario", "matriz_costos", "modulo_a_busqueda_heuristica",
                  "modulo_b_busqueda_local", "modulo_c_metaheuristicas",
                  "modulo_d_teoria_juegos", "modulo_e_minimax",
                  "planificacion_final"):
        assert clave in resultado

    plan = resultado["planificacion_final"]
    assert plan["ruta_nombres"][0] == "Inicio"
    assert plan["ruta_nombres"][-1] == "Destino"
    assert len(plan["ruta_nombres"]) == len(escenario.entregas) + 2
    assert sorted(plan["orden_posiciones"]) == list(range(len(escenario.entregas)))
    assert plan["costo_total_integrado"] >= plan["costo_ruta_base"]
    assert plan["factor_competidor"] >= 1.0
    assert "asignacion_recursos" in plan

    # Todos los módulos usan la misma matriz y las mismas entregas.
    assert len(resultado["matriz_costos"]["puntos"]) == len(escenario.entregas) + 2
    assert len(resultado["modulo_a_busqueda_heuristica"]["a_estrella"]["camino"]) > 0
    assert len(resultado["modulo_d_teoria_juegos"]["matriz"]) == 3
    assert resultado["modulo_e_minimax"]["valores_iguales"] is True
    assert resultado["modulo_c_metaheuristicas"]["recocido_simulado"]["mejor_costo"] > 0
    assert resultado["modulo_c_metaheuristicas"]["algoritmo_genetico"]["mejor_costo"] > 0


def test_ruta_final_evita_obstaculos(escenario):
    resultado = ejecutar_planificacion(escenario, _parametros_rapidos())
    for x, y in resultado["planificacion_final"]["ruta_coordenadas"]:
        assert escenario.mapa.es_transitable(x, y)


def test_competidor_afecta_planificacion(escenario):
    parametros = _parametros_rapidos()
    base = ejecutar_planificacion(escenario, parametros)

    agresivo = escenario
    agresivo.competidor = dict(escenario.competidor)
    agresivo.competidor["efecto_costo"] = 1.5
    alterado = ejecutar_planificacion(agresivo, parametros)

    assert alterado["planificacion_final"]["factor_competidor"] >= \
        base["planificacion_final"]["factor_competidor"]
