# -*- coding: utf-8 -*-
"""
Módulo D: Teoría de juegos.

Juego de dos jugadores con tres estrategias cada uno:
  Jugador 1 (empresa logística): ruta rápida, ruta económica, reserva preventiva.
  Jugador 2 (competidor): bloqueo de ruta, presión de costos, no intervención.

La matriz de pagos se construye a partir del escenario real: ingreso por
demanda, costo de la ruta calculada con A*, recursos disponibles, efecto del
competidor y consumo relativo de cada estrategia. No se escribe a mano el
resultado de los equilibrios: se calculan matemáticamente sobre la matriz.

Convención de la matriz:
    filas    -> estrategias de la empresa,
    columnas -> estrategias del competidor,
    cada celda contiene (pago_empresa, pago_competidor).
"""

from __future__ import annotations

ESTRATEGIAS_EMPRESA = [
    "Ruta rápida",
    "Ruta económica",
    "Reserva preventiva",
]

ESTRATEGIAS_COMPETIDOR = [
    "Bloqueo de ruta",
    "Presión de costos",
    "No intervención",
]

_MULT_COSTO_EMPRESA = [0.85, 1.00, 1.15]
_FACTOR_RECURSOS_EMPRESA = [1.30, 0.90, 0.65]
_MULT_COSTO_COMPETIDOR = {
    "Bloqueo de ruta": [1.25, 1.10, 1.02],
    "Presión de costos": [1.12, 1.18, 0.98],
    "No intervención": [1.00, 1.00, 1.00],
}
_CAPTURA_COMPETIDOR = {
    "Bloqueo de ruta": 0.45,
    "Presión de costos": 0.35,
    "No intervención": 0.10,
}
_COSTO_COMPETIDOR = {
    "Bloqueo de ruta": 0.15,
    "Presión de costos": 0.10,
    "No intervención": 0.02,
}


def construir_matriz_pagos(escenario, costo_base):
    """
    Construye la matriz 3x3 de pagos usando datos del escenario.

    Fórmulas documentadas:
      ingreso = suma(demanda de entregas) * 10
      costo_ruta = costo_base * mult_empresa * mult_competidor
      penalizacion = recursos_totales * 0.02 * factor_recursos * captura
      pago_empresa = ingreso - costo_ruta - penalizacion
      pago_competidor = costo_ruta * captura + costo_base*0.10
                        - costo_base * costo_competidor
    """
    ingreso = sum(e.demanda for e in escenario.entregas) * 10.0
    base = max(1.0, float(costo_base))
    recursos_totales = sum(escenario.recursos.values()) or 1.0
    competidor = escenario.competidor or {}
    efecto_extra = float(competidor.get("efecto_costo", 1.0))

    matriz = []
    for i, _ in enumerate(ESTRATEGIAS_EMPRESA):
        fila = []
        for j, estrategia_comp in enumerate(ESTRATEGIAS_COMPETIDOR):
            mult_comp = _MULT_COSTO_COMPETIDOR[estrategia_comp][i] * efecto_extra
            costo_ruta = base * _MULT_COSTO_EMPRESA[i] * mult_comp
            captura = _CAPTURA_COMPETIDOR[estrategia_comp]
            penalizacion = (recursos_totales * 0.02
                            * _FACTOR_RECURSOS_EMPRESA[i] * captura)
            pago_empresa = ingreso - costo_ruta - penalizacion
            pago_competidor = (costo_ruta * captura + base * 0.10
                               - base * _COSTO_COMPETIDOR[estrategia_comp])
            fila.append({
                "empresa": round(pago_empresa, 2),
                "competidor": round(pago_competidor, 2),
                "costo_ruta": round(costo_ruta, 2),
                "penalizacion_recursos": round(penalizacion, 2),
                "factor_costo": round(costo_ruta / base, 4),
            })
        matriz.append(fila)

    return {
        "jugadores": {
            "empresa": "Jugador 1 - Empresa logística (MAX)",
            "competidor": "Jugador 2 - Competidor (MAX de su propio pago)",
        },
        "estrategias_empresa": ESTRATEGIAS_EMPRESA,
        "estrategias_competidor": ESTRATEGIAS_COMPETIDOR,
        "matriz": matriz,
        "datos_base": {
            "ingreso_por_demanda": round(ingreso, 2),
            "costo_base_astar": round(base, 2),
            "recursos_totales": round(recursos_totales, 2),
            "efecto_extra_competidor": round(efecto_extra, 4),
        },
    }


def mejores_respuestas(matriz):
    """Mejores respuestas de ambos jugadores para cada estrategia rival."""
    n_emp = len(matriz)
    n_comp = len(matriz[0]) if n_emp else 0

    empresa = []
    for j in range(n_comp):
        pagos = [matriz[i][j]["empresa"] for i in range(n_emp)]
        maximo = max(pagos)
        empresa.append({
            "competidor": ESTRATEGIAS_COMPETIDOR[j],
            "mejores_empresa": [ESTRATEGIAS_EMPRESA[i] for i in range(n_emp)
                                if abs(pagos[i] - maximo) <= 1e-9],
            "pago_maximo": round(maximo, 2),
        })

    competidor = []
    for i in range(n_emp):
        pagos = [matriz[i][j]["competidor"] for j in range(n_comp)]
        maximo = max(pagos)
        competidor.append({
            "empresa": ESTRATEGIAS_EMPRESA[i],
            "mejores_competidor": [ESTRATEGIAS_COMPETIDOR[j] for j in range(n_comp)
                                   if abs(pagos[j] - maximo) <= 1e-9],
            "pago_maximo": round(maximo, 2),
        })

    return {"empresa": empresa, "competidor": competidor}


def _dominancia(pagos_por_estrategia, etiquetas):
    """Detecta dominancia débil y estricta entre estrategias del mismo jugador."""
    n = len(pagos_por_estrategia)
    dominantes = []
    dominadas = []
    for i in range(n):
        for k in range(n):
            if i == k:
                continue
            a = pagos_por_estrategia[i]
            b = pagos_por_estrategia[k]
            if all(x >= y - 1e-9 for x, y in zip(a, b)):
                estricta = any(x > y + 1e-9 for x, y in zip(a, b))
                dominantes.append({
                    "estrategia": etiquetas[i],
                    "domina_a": etiquetas[k],
                    "estricta": estricta,
                })
                dominadas.append({
                    "estrategia": etiquetas[k],
                    "dominada_por": etiquetas[i],
                    "estricta": estricta,
                })
    return {"dominantes": dominantes, "dominadas": dominadas}


def _dominantes_sobre_todas(pagos_por_estrategia, etiquetas):
    """Estrategias que dominan a TODAS las demás del mismo jugador.

    Una estrategia i es dominante estricta si su pago es mayor que el de cada
    otra estrategia k frente a toda respuesta del rival; es dominante débil si
    es mayor o igual en todas y estrictamente mayor en al menos una. Dominar a
    una sola estrategia (dominancia por pares) no basta para ser dominante.
    """
    n = len(pagos_por_estrategia)
    resultado = []
    for i in range(n):
        otras = [k for k in range(n) if k != i]
        a = pagos_por_estrategia[i]
        estricta = all(all(x > y + 1e-9 for x, y in zip(a, pagos_por_estrategia[k]))
                       for k in otras)
        debil = all(
            all(x >= y - 1e-9 for x, y in zip(a, pagos_por_estrategia[k]))
            and any(x > y + 1e-9 for x, y in zip(a, pagos_por_estrategia[k]))
            for k in otras)
        if estricta or debil:
            resultado.append({"estrategia": etiquetas[i],
                              "tipo": "estricta" if estricta else "débil"})
    return resultado


def dominancia(matriz):
    n_emp = len(matriz)
    n_comp = len(matriz[0]) if n_emp else 0
    pagos_empresa = [[matriz[i][j]["empresa"] for j in range(n_comp)]
                     for i in range(n_emp)]
    pagos_competidor = [[matriz[i][j]["competidor"] for i in range(n_emp)]
                        for j in range(n_comp)]
    resultado = {
        "empresa": _dominancia(pagos_empresa, ESTRATEGIAS_EMPRESA),
        "competidor": _dominancia(pagos_competidor, ESTRATEGIAS_COMPETIDOR),
    }
    resultado["empresa"]["dominantes_sobre_todas"] = _dominantes_sobre_todas(
        pagos_empresa, ESTRATEGIAS_EMPRESA)
    resultado["competidor"]["dominantes_sobre_todas"] = _dominantes_sobre_todas(
        pagos_competidor, ESTRATEGIAS_COMPETIDOR)
    return resultado


def equilibrios_nash(matriz):
    """Equilibrios de Nash puros: cada jugador responde óptimamente al rival."""
    n_emp = len(matriz)
    n_comp = len(matriz[0]) if n_emp else 0
    equilibrios = []
    for i in range(n_emp):
        for j in range(n_comp):
            pago_emp = matriz[i][j]["empresa"]
            pago_comp = matriz[i][j]["competidor"]
            mejor_emp = all(matriz[k][j]["empresa"] <= pago_emp + 1e-9
                            for k in range(n_emp))
            mejor_comp = all(matriz[i][k]["competidor"] <= pago_comp + 1e-9
                             for k in range(n_comp))
            if mejor_emp and mejor_comp:
                equilibrios.append({
                    "fila": i,
                    "columna": j,
                    "empresa": ESTRATEGIAS_EMPRESA[i],
                    "competidor": ESTRATEGIAS_COMPETIDOR[j],
                    "pago_empresa": pago_emp,
                    "pago_competidor": pago_comp,
                })
    return equilibrios


def _caracterizar_equilibrio(matriz, equilibrio):
    """Datos que sustentan el equilibrio (no se infieren de comparar celdas).

    - desviaciones: pago de cada jugador si cambia unilateralmente.
    - estricto: ninguna desviación iguala el pago actual (Nash estricto).
    - eficiente_pareto: ninguna otra celda mejora a un jugador sin empeorar
      al otro.
    """
    i, j = equilibrio["fila"], equilibrio["columna"]
    n_emp, n_comp = len(matriz), len(matriz[0])
    pe, pc = matriz[i][j]["empresa"], matriz[i][j]["competidor"]
    desv_emp = {ESTRATEGIAS_EMPRESA[k]: matriz[k][j]["empresa"]
                for k in range(n_emp) if k != i}
    desv_comp = {ESTRATEGIAS_COMPETIDOR[k]: matriz[i][k]["competidor"]
                 for k in range(n_comp) if k != j}
    estricto = (all(v < pe - 1e-9 for v in desv_emp.values())
                and all(v < pc - 1e-9 for v in desv_comp.values()))
    dominada = False
    for a in range(n_emp):
        for b in range(n_comp):
            if (a, b) == (i, j):
                continue
            ea, ca = matriz[a][b]["empresa"], matriz[a][b]["competidor"]
            if ea >= pe - 1e-9 and ca >= pc - 1e-9 and (
                    ea > pe + 1e-9 or ca > pc + 1e-9):
                dominada = True
    return {
        "desviaciones_empresa": desv_emp,
        "desviaciones_competidor": desv_comp,
        "estricto": estricto,
        "eficiente_pareto": not dominada,
    }


def interpretar(escenario, equilibrios, dominancia_resultado):
    """Genera una interpretación textual basada en el análisis calculado."""
    notas = []
    if equilibrios:
        for eq in equilibrios:
            notas.append(
                "Equilibrio de Nash puro: la empresa elige '{}' y el competidor "
                "'{}'. Ninguno mejora su pago cambiando solo su estrategia.".format(
                    eq["empresa"], eq["competidor"]))
    else:
        notas.append(
            "No existe equilibrio de Nash puro en la matriz calculada; "
            "el análisis debe considerar estrategias mixtas.")

    for jugador, clave in (("La empresa", "empresa"),
                           ("El competidor", "competidor")):
        dom = dominancia_resultado[clave]["dominantes_sobre_todas"]
        if dom:
            notas.append(
                "{} tiene estrategia dominante {}: '{}'.".format(
                    jugador, dom[0]["tipo"], dom[0]["estrategia"]))
        else:
            notas.append(
                "{} no tiene una estrategia dominante sobre todas las demás."
                .format(jugador))

    for eq in equilibrios:
        car = eq.get("caracterizacion")
        if car:
            notas.append(
                "El equilibrio ({}, {}) es {} y {} eficiente en el sentido de "
                "Pareto.".format(
                    eq["empresa"], eq["competidor"],
                    "estricto" if car["estricto"] else "débil",
                    "es" if car["eficiente_pareto"] else "no es"))

    notas.append(
        "El competidor '{}' puede elevar el costo de ruta o reducir recursos; "
        "la empresa debe decidir entre rapidez, economía y reserva preventiva."
        .format(escenario.competidor.get("nombre", "rival")))

    return notas


def analizar_juego(escenario, costo_base):
    juego = construir_matriz_pagos(escenario, costo_base)
    matriz = juego["matriz"]
    respuestas = mejores_respuestas(matriz)
    dom = dominancia(matriz)
    nash = equilibrios_nash(matriz)
    for eq in nash:
        eq["caracterizacion"] = _caracterizar_equilibrio(matriz, eq)
    juego.update({
        "mejores_respuestas": respuestas,
        "dominancia": dom,
        "equilibrios_nash": nash,
        "interpretacion": interpretar(escenario, nash, dom),
    })
    return juego
