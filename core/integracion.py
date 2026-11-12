# -*- coding: utf-8 -*-
"""
Integración de los cinco módulos sobre un mismo escenario.

Flujo:
  1. Validación del escenario.
  2. Matriz de costos mínimos entre Inicio, entregas y Destino (A*).
  3. Módulo A: Greedy Best-First vs A*.
  4. Módulo B: Hill Climbing sobre el orden de entregas.
  5. Módulo C: recocido simulado y algoritmo genético.
  6. Módulo D: teoría de juegos con el competidor.
  7. Módulo E: Minimax y poda alfa-beta sobre contratos de recursos.
  8. Planificación final: se elige el mejor orden y se aplican los efectos
     del competidor y la asignación de recursos.

Todos los módulos reciben la misma instancia (core.escenario.Escenario) y
la misma matriz de costos; no hay copias ni escenarios paralelos.
"""

from __future__ import annotations

import json
import os
import time

from algoritmos.algoritmo_genetico import algoritmo_genetico
from algoritmos.busqueda_heuristica import comparar_greedy_a_estrella
from algoritmos.busqueda_local import hill_climbing
from algoritmos.minimax import comparar_minimax_alfa_beta
from algoritmos.recocido_simulado import recocido_simulado
from algoritmos.teoria_juegos import analizar_juego
from core.costos import (construir_matriz_costos, costo_orden,
                         nombres_orden, ruta_coordenadas)

RUTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_PARAMETROS = os.path.join(RUTA_RAIZ, "config", "parametros.json")

PARAMETROS_POR_DEFECTO = {
    "semilla_global": 42,
    "busqueda_local": {"soluciones_iniciales": 10, "max_iteraciones": 200},
    "recocido_simulado": {
        "temperatura_inicial": 50.0,
        "temperatura_final": 0.01,
        "factor_enfriamiento": 0.97,
        "iteraciones_por_temperatura": 40,
    },
    "algoritmo_genetico": {
        "tamano_poblacion": 60,
        "generaciones": 150,
        "prob_mutacion": 0.15,
        "prob_cruce": 0.9,
        "tamanio_torneo": 3,
        "elitismo": True,
    },
    "minimax": {"profundidad_maxima": 12},
}

_COSTO_UNITARIO_RECURSO = {
    "combustible": 8.0,
    "permisos": 25.0,
    "tiempo": 3.0,
}


def cargar_parametros(ruta=RUTA_PARAMETROS):
    """Carga config/parametros.json y completa claves faltantes."""
    parametros = json.loads(json.dumps(PARAMETROS_POR_DEFECTO))
    if os.path.isfile(ruta):
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        for clave, valor in datos.items():
            if isinstance(valor, dict) and isinstance(parametros.get(clave), dict):
                parametros[clave].update(valor)
            else:
                parametros[clave] = valor
    return parametros


def _serializar_matriz(matriz):
    return [
        [(None if (v == float("inf") or v != v) else round(float(v), 4)) for v in fila]
        for fila in matriz
    ]


def _matriz_costos_serializable(datos_costos):
    return {
        "puntos": datos_costos["puntos"],
        "coordenadas": [list(c) for c in datos_costos["coordenadas"]],
        "matriz": _serializar_matriz(datos_costos["matriz"]),
        "inalcanzables": datos_costos["inalcanzables"],
    }


def _elegir_competidor(juego):
    """Selecciona la estrategia rival más desfavorable entre los Nash puros."""
    nash = juego.get("equilibrios_nash") or []
    if nash:
        elegido = min(nash, key=lambda eq: eq["pago_empresa"])
        return elegido, "equilibrio de Nash puro (peor pago para la empresa)"
    return None, "no hay Nash puro; se usa el peor caso del competidor"


def _peor_caso_competidor(juego):
    """Si no hay Nash, usa la columna que minimiza el mejor pago de la empresa."""
    matriz = juego["matriz"]
    n_comp = len(juego["estrategias_competidor"])
    peor_columna = 0
    peor_valor = float("inf")
    for j in range(n_comp):
        mejor_empresa = max(matriz[i][j]["empresa"] for i in range(len(matriz)))
        if mejor_empresa < peor_valor:
            peor_valor = mejor_empresa
            peor_columna = j
    i_empresa = max(
        range(len(matriz)),
        key=lambda i: matriz[i][peor_columna]["empresa"])
    return {
        "fila": i_empresa,
        "columna": peor_columna,
        "empresa": juego["estrategias_empresa"][i_empresa],
        "competidor": juego["estrategias_competidor"][peor_columna],
        "pago_empresa": matriz[i_empresa][peor_columna]["empresa"],
        "pago_competidor": matriz[i_empresa][peor_columna]["competidor"],
    }


def _asignacion_recursos(escenario, minimax_resultado):
    """
    Traduce el valor minimax en una fracción de recursos que conserva la
    empresa. Si el competidor niega contratos, la fracción baja y pueden
    aparecer déficits que encarecen la planificación final.
    """
    contratos = minimax_resultado.get("contratos") or []
    total = sum(c["valor"] for c in contratos) or 1.0
    valor = float(minimax_resultado.get("valor_minimax", 0.0))
    valor_max = (total + valor) / 2.0
    fraccion = max(0.0, min(1.0, valor_max / total))

    requeridos = escenario.recursos_requeridos()
    detalle = {}
    penalizacion = 0.0
    deficit_total = 0.0
    for clave, requerido in requeridos.items():
        disponible_base = float(escenario.recursos.get(clave, 0))
        disponible = round(disponible_base * fraccion, 2)
        deficit = max(0.0, requerido - disponible)
        costo_unitario = _COSTO_UNITARIO_RECURSO.get(clave, 10.0)
        costo_deficit = deficit * costo_unitario
        detalle[clave] = {
            "disponible_base": round(disponible_base, 2),
            "fraccion_conservada": round(fraccion, 4),
            "disponible_efectivo": disponible,
            "requerido": requerido,
            "deficit": round(deficit, 2),
            "costo_por_deficit": round(costo_deficit, 2),
        }
        penalizacion += costo_deficit
        deficit_total += deficit

    return {
        "fraccion_recursos_conservada": round(fraccion, 4),
        "detalle": detalle,
        "deficit_total": round(deficit_total, 2),
        "penalizacion_por_deficit": round(penalizacion, 2),
        "recursos_suficientes": deficit_total <= 1e-9,
    }


def ejecutar_planificacion(escenario, parametros=None):
    """Ejecuta el flujo completo e integra los resultados."""
    inicio_total = time.perf_counter()
    parametros = parametros or cargar_parametros()
    semilla = int(parametros.get("semilla_global", escenario.semilla))

    errores = escenario.validar()
    if errores:
        raise ValueError("; ".join(errores))

    datos_costos = construir_matriz_costos(escenario)
    if datos_costos["inalcanzables"]:
        pares = ", ".join(
            "{}->{}".format(datos_costos["puntos"][a], datos_costos["puntos"][b])
            for a, b in datos_costos["inalcanzables"])
        raise ValueError("Hay puntos sin ruta transitable: " + pares)

    # Módulo A: búsqueda heurística desde Inicio hasta Destino.
    heuristicas = comparar_greedy_a_estrella(
        escenario.mapa, escenario.inicio, escenario.destino)
    if not heuristicas["a_estrella"]["encontrado"]:
        raise ValueError("A* no encontró una ruta entre Inicio y Destino.")

    n_entregas = len(escenario.entregas)

    # Módulo B: búsqueda local.
    config_local = parametros.get("busqueda_local", {})
    local = hill_climbing(
        datos_costos["matriz"], n_entregas=n_entregas,
        soluciones_iniciales=config_local.get("soluciones_iniciales", 10),
        max_iteraciones=config_local.get("max_iteraciones", 200),
        semilla=semilla)

    # Módulo C: recocido simulado y algoritmo genético.
    config_sa = parametros.get("recocido_simulado", {})
    sa = recocido_simulado(
        datos_costos["matriz"], n_entregas=n_entregas,
        temperatura_inicial=config_sa.get("temperatura_inicial", 50.0),
        temperatura_final=config_sa.get("temperatura_final", 0.01),
        factor_enfriamiento=config_sa.get("factor_enfriamiento", 0.97),
        iteraciones_por_temperatura=config_sa.get(
            "iteraciones_por_temperatura", 40),
        semilla=semilla)

    config_ga = parametros.get("algoritmo_genetico", {})
    ga = algoritmo_genetico(
        datos_costos["matriz"], n_entregas=n_entregas,
        tamano_poblacion=config_ga.get("tamano_poblacion", 60),
        generaciones=config_ga.get("generaciones", 150),
        prob_mutacion=config_ga.get("prob_mutacion", 0.15),
        prob_cruce=config_ga.get("prob_cruce", 0.9),
        tamanio_torneo=config_ga.get("tamanio_torneo", 3),
        elitismo=config_ga.get("elitismo", True),
        semilla=semilla)

    candidatos = [
        ("Hill Climbing", local["mejor"]["orden"], local["mejor"]["costo"]),
        ("Recocido simulado", sa["mejor_orden"], sa["mejor_costo"]),
        ("Algoritmo genético", ga["mejor_orden"], ga["mejor_costo"]),
    ]
    origen_mejor, mejor_orden, mejor_costo = min(candidatos, key=lambda c: c[2])
    mejor_costo = float(mejor_costo)
    indices_matriz = [i + 1 for i in mejor_orden]

    # Módulo D: teoría de juegos.
    juego = analizar_juego(
        escenario, heuristicas["a_estrella"]["costo"] or mejor_costo)
    equilibrio, criterio_competidor = _elegir_competidor(juego)
    if equilibrio is None:
        equilibrio = _peor_caso_competidor(juego)
    celda = juego["matriz"][equilibrio["fila"]][equilibrio["columna"]]
    factor_competidor = float(celda.get("factor_costo", 1.0))

    # Módulo E: minimax y poda alfa-beta.
    config_minimax = parametros.get("minimax", {})
    profundidad = config_minimax.get("profundidad_maxima", n_entregas)
    minimax_info = comparar_minimax_alfa_beta(escenario, profundidad)
    asignacion = _asignacion_recursos(
        escenario, minimax_info["con_poda"])

    # Planificación final integrada.
    costo_ruta_base = costo_orden(indices_matriz, datos_costos["matriz"])
    costo_ruta_competidor = costo_ruta_base * factor_competidor
    costo_total = costo_ruta_competidor + asignacion["penalizacion_por_deficit"]
    ruta_coords = ruta_coordenadas(indices_matriz, datos_costos)
    nombres = nombres_orden(indices_matriz, datos_costos)

    advertencias = []
    if not asignacion["recursos_suficientes"]:
        advertencias.append(
            "El competidor reduce recursos: se requiere adquirir el déficit "
            "y se añade una penalización de {:.2f}.".format(
                asignacion["penalizacion_por_deficit"]))
    if ga.get("posible_convergencia_prematura"):
        advertencias.append(
            "El algoritmo genético muestra posible convergencia prematura "
            "(sin mejora durante {} generaciones).".format(
                ga.get("generaciones_sin_mejora", 0)))

    planificacion = {
        "algoritmo_origen": origen_mejor,
        "orden_entregas": [escenario.entregas[i].nombre for i in mejor_orden],
        "orden_posiciones": mejor_orden,
        "ruta_nombres": nombres,
        "ruta_coordenadas": [list(c) for c in ruta_coords],
        "costo_ruta_base": round(costo_ruta_base, 4),
        "factor_competidor": round(factor_competidor, 4),
        "costo_ruta_ajustado": round(costo_ruta_competidor, 4),
        "penalizacion_recursos": round(
            asignacion["penalizacion_por_deficit"], 4),
        "costo_total_integrado": round(costo_total, 4),
        "estrategia_empresa": equilibrio["empresa"],
        "estrategia_competidor": equilibrio["competidor"],
        "criterio_seleccion_competidor": criterio_competidor,
        "asignacion_recursos": asignacion,
        "advertencias": advertencias,
        "factible_sin_adquisicion": asignacion["recursos_suficientes"],
    }

    comparacion_metodos = [
        {"metodo": "Hill Climbing", "costo": round(local["mejor"]["costo"], 4),
         "evaluaciones": local["evaluaciones"],
         "tiempo_ms": local["tiempo_total_ms"]},
        {"metodo": "Recocido simulado", "costo": round(sa["mejor_costo"], 4),
         "evaluaciones": sa["evaluaciones"], "tiempo_ms": sa["tiempo_ms"]},
        {"metodo": "Algoritmo genético", "costo": round(ga["mejor_costo"], 4),
         "evaluaciones": ga["evaluaciones"], "tiempo_ms": ga["tiempo_ms"]},
    ]
    mejor_de_metodos = min(comparacion_metodos, key=lambda c: c["costo"])
    for fila in comparacion_metodos:
        fila["mejor"] = fila["metodo"] == mejor_de_metodos["metodo"]

    return {
        "escenario": escenario.to_dict(),
        "validacion": {"valido": True, "errores": []},
        "matriz_costos": _matriz_costos_serializable(datos_costos),
        "modulo_a_busqueda_heuristica": heuristicas,
        "modulo_b_busqueda_local": local,
        "modulo_c_metaheuristicas": {
            "recocido_simulado": sa,
            "algoritmo_genetico": ga,
            "comparacion": comparacion_metodos,
        },
        "modulo_d_teoria_juegos": juego,
        "modulo_e_minimax": minimax_info,
        "planificacion_final": planificacion,
        "tiempo_total_ms": round(
            (time.perf_counter() - inicio_total) * 1000.0, 3),
    }
