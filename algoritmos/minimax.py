# -*- coding: utf-8 -*-
"""
Módulo E: Minimax y poda alfa-beta.

MODELO DEL JUEGO (suma cero, por turnos, información perfecta)
--------------------------------------------------------------
Subproblema de la planificación: la empresa (MAX) y el competidor (MIN) se
disputan el acceso prioritario a las entregas del escenario. Cada entrega es
un "contrato" c_i con valor v_i = demanda_i + 5 (la prima de 5 representa la
prioridad comercial de atender una entrega).

  Estado      s = (R, A_max, A_min, turno)
              R: contratos disponibles; A_max, A_min: contratos ya asignados
              a cada jugador; turno en {MAX, MIN}. Estado inicial: R = todos
              los contratos, A_max = A_min = vacío, juega MAX.
  Acciones    acciones(s) = R (cualquier contrato disponible).
  Transición  el jugador en turno mueve el contrato elegido de R a su
              conjunto; el turno pasa al rival (MAX y MIN alternan).
  Terminal    R vacío (todos los contratos asignados). Con n contratos el
              árbol tiene profundidad n.
  Utilidad    U(s) = sum(v_i, i en A_max) - sum(v_i, i en A_min), desde el
              punto de vista de MAX. MAX maximiza U y MIN la minimiza.

Con límite de profundidad d < n, el nodo a profundidad d (no terminal) se
valora con una evaluación aproximada: se supone que los contratos restantes
se reparten de forma voraz, alternando desde quien tiene el turno (cada
jugador toma el de mayor valor disponible):
      U_aprox = U_actual + signo(turno) * (v(1) - v(2) + v(3) - ...)
donde v(1) >= v(2) >= ... son los valores restantes ordenados de mayor a
menor y signo(MAX) = +1, signo(MIN) = -1.

Orden de las acciones: por valor descendente (igual en minimax y alfa-beta,
de modo que ambos exploran el mismo árbol). La poda alfa-beta no cambia el
valor minimax; solo reduce los nodos visitados.

Contadores:
  nodos_visitados: nodos del árbol en los que se ejecutó la función.
  nodos_podados:   nodos de los subárboles omitidos por la poda (se calculan
                   de forma exacta). Se cumple:
                   visitados_alfa_beta + podados = visitados_minimax.
  cortes:          número de veces que se activó la condición alfa >= beta.
"""

from __future__ import annotations

import time


def construir_contratos(escenario):
    """Convierte las entregas en contratos de recurso con valor."""
    contratos = []
    for entrega in escenario.entregas:
        contratos.append({
            "indice": len(contratos),
            "id": entrega.id,
            "nombre": entrega.nombre,
            "valor": float(entrega.demanda + 5),
            "demanda": int(entrega.demanda),
        })
    return contratos


def _utilidad(claims_max, claims_min, contratos):
    valor_max = sum(contratos[i]["valor"] for i in claims_max)
    valor_min = sum(contratos[i]["valor"] for i in claims_min)
    return valor_max - valor_min


def _evaluacion(claims_max, claims_min, restantes, contratos, turno):
    """Evaluación aproximada: reparto voraz alternado de los restantes."""
    utilidad = _utilidad(claims_max, claims_min, contratos)
    valores = sorted((contratos[i]["valor"] for i in restantes), reverse=True)
    signo = 1.0 if turno == "MAX" else -1.0
    for k, v in enumerate(valores):
        utilidad += signo * v if k % 2 == 0 else -signo * v
    return utilidad


def _nodos_subarbol(n_restantes, profundidad_disponible):
    """Número de nodos de un subárbol completo (raíz incluida).

    Cada nodo con r contratos restantes tiene r hijos; el subárbol se detiene
    en r = 0 o al agotar la profundidad permitida.
    """
    if n_restantes == 0 or profundidad_disponible == 0:
        return 1
    return 1 + n_restantes * _nodos_subarbol(n_restantes - 1,
                                             profundidad_disponible - 1)


def _ordenar_acciones(restantes, contratos):
    return sorted(restantes, key=lambda i: contratos[i]["valor"], reverse=True)


def _minimax_rec(restantes, claims_max, claims_min, turno, profundidad,
                 profundidad_maxima, contratos, contadores, alpha=None,
                 beta=None, usar_poda=False):
    contadores["visitados"] += 1

    if not restantes or profundidad >= profundidad_maxima:
        if not restantes:
            return _utilidad(claims_max, claims_min, contratos), []
        return _evaluacion(claims_max, claims_min, restantes, contratos,
                           turno), []

    acciones = _ordenar_acciones(restantes, contratos)

    if turno == "MAX":
        mejor_valor = float("-inf")
        mejor_camino = []
        for accion in acciones:
            nuevas_restantes = tuple(i for i in restantes if i != accion)
            valor, camino = _minimax_rec(
                nuevas_restantes, claims_max + (accion,), claims_min, "MIN",
                profundidad + 1, profundidad_maxima, contratos, contadores,
                alpha, beta, usar_poda)
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_camino = [accion] + camino
            if usar_poda:
                alpha = max(alpha, mejor_valor)
                if alpha >= beta:
                    omitidas = len(acciones) - acciones.index(accion) - 1
                    contadores["cortes"] += 1
                    contadores["podados"] += omitidas * _nodos_subarbol(
                        len(restantes) - 1, profundidad_maxima - profundidad - 1)
                    break
        return mejor_valor, mejor_camino

    mejor_valor = float("inf")
    mejor_camino = []
    for accion in acciones:
        nuevas_restantes = tuple(i for i in restantes if i != accion)
        valor, camino = _minimax_rec(
            nuevas_restantes, claims_max, claims_min + (accion,), "MAX",
            profundidad + 1, profundidad_maxima, contratos, contadores,
            alpha, beta, usar_poda)
        if valor < mejor_valor:
            mejor_valor = valor
            mejor_camino = [accion] + camino
        if usar_poda:
            beta = min(beta, mejor_valor)
            if beta <= alpha:
                omitidas = len(acciones) - acciones.index(accion) - 1
                contadores["cortes"] += 1
                contadores["podados"] += omitidas * _nodos_subarbol(
                    len(restantes) - 1, profundidad_maxima - profundidad - 1)
                break
    return mejor_valor, mejor_camino


def _ejecutar(escenario, profundidad_maxima, usar_poda):
    contratos = construir_contratos(escenario)
    if not contratos:
        return {
            "valor_minimax": 0.0,
            "mejor_decision": None,
            "nodos_visitados": 0,
            "nodos_podados": 0,
            "profundidad_utilizada": 0,
            "tiempo_ms": 0.0,
            "contratos": [],
            "mensaje": "No hay entregas para formar contratos de recurso.",
        }

    if profundidad_maxima is None:
        profundidad_maxima = len(contratos)
    profundidad_maxima = max(1, min(int(profundidad_maxima), len(contratos)))

    contadores = {"visitados": 0, "podados": 0, "cortes": 0}
    inicio = time.perf_counter()
    valor, camino = _minimax_rec(
        tuple(range(len(contratos))), tuple(), tuple(), "MAX", 0,
        profundidad_maxima, contratos, contadores,
        float("-inf"), float("inf"), usar_poda)
    tiempo = round((time.perf_counter() - inicio) * 1000.0, 3)

    claims_max = [camino[i] for i in range(len(camino)) if i % 2 == 0]
    claims_min = [camino[i] for i in range(len(camino)) if i % 2 == 1]
    return {
        "valor_minimax": round(float(valor), 4),
        "mejor_decision": contratos[camino[0]]["nombre"] if camino else None,
        "mejor_decision_id": contratos[camino[0]]["id"] if camino else None,
        "linea_principal": [contratos[i]["nombre"] for i in camino],
        "contratos_max": [contratos[i]["nombre"] for i in claims_max],
        "contratos_min": [contratos[i]["nombre"] for i in claims_min],
        "nodos_visitados": contadores["visitados"],
        "nodos_podados": contadores["podados"],
        "cortes_alfa_beta": contadores["cortes"],
        "profundidad_utilizada": profundidad_maxima,
        "profundidad_completa": profundidad_maxima >= len(contratos),
        "uso_poda_alfa_beta": bool(usar_poda),
        "tiempo_ms": tiempo,
        "contratos": contratos,
        "evaluacion": ("utilidad exacta" if profundidad_maxima >= len(contratos)
                       else "evaluación aproximada (reparto voraz alternado)"),
        "mensaje": "Decisión calculada sobre contratos de acceso a entregas.",
    }


def minimax(escenario, profundidad_maxima=None):
    """Minimax sin poda."""
    return _ejecutar(escenario, profundidad_maxima, usar_poda=False)


def minimax_alfa_beta(escenario, profundidad_maxima=None):
    """Minimax con poda alfa-beta."""
    return _ejecutar(escenario, profundidad_maxima, usar_poda=True)


def comparar_minimax_alfa_beta(escenario, profundidad_maxima=None,
                               repeticiones_tiempo=15):
    """Verifica que ambos métodos produzcan el mismo valor minimax.

    Los nodos son deterministas. El tiempo se reporta como la mediana de
    `repeticiones_tiempo` ejecuciones tras una de calentamiento, porque una
    sola medición de milisegundos es muy sensible al ruido del sistema.
    """
    def medir(usar_poda):
        _ejecutar(escenario, profundidad_maxima, usar_poda)  # calentamiento
        corridas = [_ejecutar(escenario, profundidad_maxima, usar_poda)
                    for _ in range(max(1, int(repeticiones_tiempo)))]
        tiempos = sorted(c["tiempo_ms"] for c in corridas)
        resultado = corridas[0]
        resultado["tiempo_ms"] = tiempos[len(tiempos) // 2]
        resultado["tiempo_ms_repeticiones"] = len(corridas)
        return resultado

    sin_poda = medir(False)
    con_poda = medir(True)
    return {
        "sin_poda": sin_poda,
        "con_poda": con_poda,
        "valores_iguales": abs(sin_poda["valor_minimax"]
                               - con_poda["valor_minimax"]) <= 1e-9,
        "nodos_ahorrados": sin_poda["nodos_visitados"] - con_poda["nodos_visitados"],
        "porcentaje_podado": round(
            100.0 * con_poda["nodos_podados"]
            / max(1, sin_poda["nodos_visitados"]), 2),
        "conteo_consistente": (con_poda["nodos_visitados"]
                               + con_poda["nodos_podados"]
                               == sin_poda["nodos_visitados"]),
    }
