# -*- coding: utf-8 -*-
"""
Sistema de experimentación reproducible.

Guarda en CSV los resultados reales de:
  - comparación Greedy vs A* en tres variantes del escenario,
  - Hill Climbing con diez soluciones iniciales,
  - recocido simulado y algoritmo genético con veinte ejecuciones cada uno,
  - teoría de juegos y comparación Minimax / alfa-beta,
  - planificación final integrada.

Genera gráficas con Matplotlib en experimentos/graficas/.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import platform
import csv
import io
import json
import os
import sys
import time

RUTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RUTA_RAIZ not in sys.path:
    sys.path.insert(0, RUTA_RAIZ)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from algoritmos.algoritmo_genetico import ejecutar_repeticiones as rep_ga
from algoritmos.busqueda_heuristica import comparar_greedy_a_estrella
from algoritmos.busqueda_local import hill_climbing
from algoritmos.minimax import comparar_minimax_alfa_beta
from algoritmos.recocido_simulado import ejecutar_repeticiones as rep_sa
from algoritmos.teoria_juegos import analizar_juego
from core.costos import construir_matriz_costos
from core.escenario import Escenario
from core.integracion import cargar_parametros, ejecutar_planificacion

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DIR_RESULTADOS = os.path.join(RUTA_RAIZ, "experimentos", "resultados")
DIR_GRAFICAS = os.path.join(RUTA_RAIZ, "experimentos", "graficas")


def huella_codigo():
    """SHA-256 de los .py y JSON de configuración: identifica la versión exacta
    del programa que produjo los resultados."""
    h = hashlib.sha256()
    for carpeta in ("algoritmos", "core", "config", "experimentos"):
        base = os.path.join(RUTA_RAIZ, carpeta)
        for raiz, _, archivos in sorted(os.walk(base)):
            for nombre in sorted(archivos):
                if nombre.endswith((".py", ".json")) and "resultados" not in raiz:
                    with open(os.path.join(raiz, nombre), "rb") as f:
                        h.update(nombre.encode() + f.read())
    return h.hexdigest()[:16]


def _asegurar_directorios():
    os.makedirs(DIR_RESULTADOS, exist_ok=True)
    os.makedirs(DIR_GRAFICAS, exist_ok=True)


def _guardar_csv(nombre, campos, filas):
    ruta = os.path.join(DIR_RESULTADOS, nombre)
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
    return ruta


def _guardar_json(nombre, datos):
    ruta = os.path.join(DIR_RESULTADOS, nombre)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    return ruta


def _procesar_figura(fig, nombre, para_web=False):
    """Renderiza la figura una sola vez, la guarda en disco y opcionalmente la devuelve en Base64."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    datos_png = buffer.getvalue()
    plt.close(fig)

    ruta = os.path.join(DIR_GRAFICAS, nombre)
    with open(ruta, "wb") as archivo:
        archivo.write(datos_png)

    if para_web:
        return base64.b64encode(datos_png).decode("utf-8")
    return None


def _clonar(escenario):
    return Escenario.desde_dict(copy.deepcopy(escenario.to_dict()))


def crear_variantes(escenario):
    """Tres escenarios distintos para probar Greedy y A*."""
    variantes = [("base", _clonar(escenario))]

    alto = _clonar(escenario)
    alto.nombre = "Costos altos"
    for y in range(alto.filas):
        for x in range(alto.columnas):
            alto.mapa.costos[y][x] = round(alto.mapa.costos[y][x] * 1.6, 2)
    variantes.append(("costos_altos", alto))

    obstruido = _clonar(escenario)
    obstruido.nombre = "Más obstáculos"
    for x, y in [(5, 5), (5, 6), (9, 5), (9, 6)]:
        if (x, y) not in obstruido.mapa.obstaculos:
            if (x, y) in [obstruido.inicio, obstruido.destino] or \
                    (x, y) in [(e.x, e.y) for e in obstruido.entregas]:
                continue
            obstruido.mapa.obstaculos.add((x, y))
    variantes.append(("mas_obstaculos", obstruido))
    return variantes


def ejecutar_experimentos(escenario=None, repeticiones=20, semilla_base=42,
                          parametros=None, guardar=True, para_web=False):
    """Ejecuta todos los experimentos y devuelve un resumen serializable."""
    inicio_total = time.perf_counter()
    escenario = escenario or Escenario.por_defecto()
    parametros = parametros or cargar_parametros()
    _asegurar_directorios()

    errores = escenario.validar()
    if errores:
        raise ValueError("; ".join(errores))

    if guardar:
        _guardar_json("parametros_experimento.json", {
            "escenario": escenario.nombre,
            "filas": escenario.filas,
            "columnas": escenario.columnas,
            "entregas": len(escenario.entregas),
            "semilla_base": semilla_base,
            "repeticiones": repeticiones,
            "parametros": parametros,
            "huella_codigo": huella_codigo(),
            "python": platform.python_version(),
            "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    imagenes = {}

    # --------------------------------------------------------------
    # 1. Búsqueda heurística en tres escenarios
    # --------------------------------------------------------------
    filas_heur = []
    resumen_heur = []
    for nombre, variante in crear_variantes(escenario):
        comparacion = comparar_greedy_a_estrella(
            variante.mapa, variante.inicio, variante.destino)
        for algoritmo in ("greedy", "a_estrella"):
            resultado = comparacion[algoritmo]
            filas_heur.append({
                "escenario": nombre,
                "semilla": semilla_base,
                "algoritmo": algoritmo,
                "encontrado": resultado["encontrado"],
                "costo": resultado["costo"],
                "nodos_expandidos": resultado["nodos_expandidos"],
                "tiempo_ms": resultado["tiempo_ms"],
                "longitud": resultado["longitud"],
                "ruta": " ".join("{},{}".format(x, y)
                                 for x, y in resultado["camino"]),
            })
        resumen_heur.append({
            "escenario": nombre,
            "costo_greedy": comparacion["greedy"]["costo"],
            "costo_astar": comparacion["a_estrella"]["costo"],
            "nodos_greedy": comparacion["greedy"]["nodos_expandidos"],
            "nodos_astar": comparacion["a_estrella"]["nodos_expandidos"],
            "tiempo_greedy_ms": comparacion["greedy"]["tiempo_ms"],
            "tiempo_astar_ms": comparacion["a_estrella"]["tiempo_ms"],
            "diferencia_costo": comparacion["diferencia_costo_a_menos_greedy"],
        })

    _guardar_csv("resultados_heuristicas.csv",
                 ["escenario", "semilla", "algoritmo", "encontrado", "costo",
                  "nodos_expandidos", "tiempo_ms", "longitud", "ruta"],
                 filas_heur)
    _guardar_csv("resumen_heuristicas.csv",
                 ["escenario", "costo_greedy", "costo_astar", "nodos_greedy",
                  "nodos_astar", "tiempo_greedy_ms", "tiempo_astar_ms",
                  "diferencia_costo"],
                 resumen_heur)

    # --------------------------------------------------------------
    # 2. Matriz de costos compartida para búsqueda local y metaheurísticas
    # --------------------------------------------------------------
    datos_costos = construir_matriz_costos(escenario)
    if datos_costos["inalcanzables"]:
        raise ValueError("El escenario contiene puntos sin ruta transitable.")
    matriz = datos_costos["matriz"]
    n_entregas = len(escenario.entregas)

    # --------------------------------------------------------------
    # 3. Hill Climbing (10 soluciones iniciales)
    # --------------------------------------------------------------
    config_local = parametros.get("busqueda_local", {})
    local = hill_climbing(
        matriz, n_entregas=n_entregas,
        soluciones_iniciales=config_local.get("soluciones_iniciales", 10),
        max_iteraciones=config_local.get("max_iteraciones", 200),
        semilla=semilla_base)
    filas_local = []
    for ejecucion in local["ejecuciones"]:
        filas_local.append({
            "escenario": escenario.nombre,
            "semilla": semilla_base + ejecucion["corrida"] - 1,
            "corrida": ejecucion["corrida"],
            "costo_inicial": ejecucion["costo_inicial"],
            "costo_final": ejecucion["costo_final"],
            "mejora": ejecucion["mejora"],
            "iteraciones": ejecucion["iteraciones"],
            "vecinos_meseta": ejecucion["vecinos_meseta"],
            "es_meseta": ejecucion["es_meseta"],
            "orden": " ".join(str(i) for i in ejecucion["orden"]),
        })
    _guardar_csv("resultados_busqueda_local.csv",
                 ["escenario", "semilla", "corrida", "costo_inicial",
                  "costo_final", "mejora", "iteraciones", "vecinos_meseta",
                  "es_meseta", "orden"],
                 filas_local)

    # --------------------------------------------------------------
    # 4. Metaheurísticas: 20 ejecuciones por método
    # --------------------------------------------------------------
    config_sa = parametros.get("recocido_simulado", {})
    sa = rep_sa(
        matriz, repeticiones=repeticiones, semilla_base=semilla_base,
        n_entregas=n_entregas,
        temperatura_inicial=config_sa.get("temperatura_inicial", 50.0),
        temperatura_final=config_sa.get("temperatura_final", 0.01),
        factor_enfriamiento=config_sa.get("factor_enfriamiento", 0.97),
        iteraciones_por_temperatura=config_sa.get(
            "iteraciones_por_temperatura", 40))

    config_ga = parametros.get("algoritmo_genetico", {})
    ga = rep_ga(
        matriz, repeticiones=repeticiones, semilla_base=semilla_base,
        n_entregas=n_entregas,
        tamano_poblacion=config_ga.get("tamano_poblacion", 60),
        generaciones=config_ga.get("generaciones", 150),
        prob_mutacion=config_ga.get("prob_mutacion", 0.15),
        prob_cruce=config_ga.get("prob_cruce", 0.9),
        tamanio_torneo=config_ga.get("tamanio_torneo", 3),
        elitismo=config_ga.get("elitismo", True))

    filas_meta = []
    for metodo, resumen in (("recocido_simulado", sa),
                            ("algoritmo_genetico", ga)):
        for corrida in resumen["corridas"]:
            filas_meta.append({
                "metodo": metodo,
                "corrida": corrida["corrida"],
                "semilla": corrida["semilla"],
                "mejor_costo": corrida["mejor_costo"],
                "evaluaciones": corrida["evaluaciones"],
                "tiempo_ms": corrida["tiempo_ms"],
                "iteraciones": corrida.get("iteraciones", corrida.get(
                    "generaciones_ejecutadas")),
                "orden": " ".join(str(i) for i in (corrida.get("mejor_orden")
                                                  or corrida.get("mejor_orden", []))),
            })
    _guardar_csv("resultados_metaheuristicas.csv",
                 ["metodo", "corrida", "semilla", "mejor_costo",
                  "evaluaciones", "tiempo_ms", "iteraciones", "orden"],
                 filas_meta)

    filas_resumen_meta = []
    for metodo, resumen in (("recocido_simulado", sa),
                            ("algoritmo_genetico", ga)):
        filas_resumen_meta.append({
            "metodo": metodo,
            "repeticiones": resumen["repeticiones"],
            "mejor_costo": resumen["mejor_costo"],
            "costo_promedio": resumen["costo_promedio"],
            "desviacion_estandar": resumen["desviacion_estandar"],
            "peor_costo": resumen["peor_costo"],
            "evaluaciones_promedio": resumen["evaluaciones_promedio"],
            "tiempo_promedio_ms": resumen["tiempo_promedio_ms"],
        })
    _guardar_csv("resumen_metaheuristicas.csv",
                 ["metodo", "repeticiones", "mejor_costo", "costo_promedio",
                  "desviacion_estandar", "peor_costo", "evaluaciones_promedio",
                  "tiempo_promedio_ms"],
                 filas_resumen_meta)

    # --------------------------------------------------------------
    # 5. Teoría de juegos y Minimax
    # --------------------------------------------------------------
    comparacion_h = comparar_greedy_a_estrella(
        escenario.mapa, escenario.inicio, escenario.destino)
    costo_base = comparacion_h["a_estrella"]["costo"] or 1.0
    juego = analizar_juego(escenario, costo_base)
    filas_juego = []
    for i, estrategia_emp in enumerate(juego["estrategias_empresa"]):
        for j, estrategia_comp in enumerate(juego["estrategias_competidor"]):
            celda = juego["matriz"][i][j]
            filas_juego.append({
                "estrategia_empresa": estrategia_emp,
                "estrategia_competidor": estrategia_comp,
                "pago_empresa": celda["empresa"],
                "pago_competidor": celda["competidor"],
                "costo_ruta": celda["costo_ruta"],
            })
    _guardar_csv("resultados_teoria_juegos.csv",
                 ["estrategia_empresa", "estrategia_competidor",
                  "pago_empresa", "pago_competidor", "costo_ruta"],
                 filas_juego)

    minimax_info = comparar_minimax_alfa_beta(
        escenario,
        parametros.get("minimax", {}).get("profundidad_maxima", n_entregas))
    filas_minimax = []
    for etiqueta, resultado in (("sin_poda", minimax_info["sin_poda"]),
                                ("alfa_beta", minimax_info["con_poda"])):
        filas_minimax.append({
            "metodo": etiqueta,
            "valor_minimax": resultado["valor_minimax"],
            "nodos_visitados": resultado["nodos_visitados"],
            "nodos_podados": resultado["nodos_podados"],
            "profundidad": resultado["profundidad_utilizada"],
            "tiempo_ms": resultado["tiempo_ms"],
            "mejor_decision": resultado["mejor_decision"],
        })
    _guardar_csv("resultados_minimax.csv",
                 ["metodo", "valor_minimax", "nodos_visitados",
                  "nodos_podados", "profundidad", "tiempo_ms",
                  "mejor_decision"],
                 filas_minimax)

    # --------------------------------------------------------------
    # 6. Planificación final integrada
    # --------------------------------------------------------------
    plan = ejecutar_planificacion(escenario, parametros)
    filas_plan = [{
        "algoritmo_origen": plan["planificacion_final"]["algoritmo_origen"],
        "costo_ruta_base": plan["planificacion_final"]["costo_ruta_base"],
        "factor_competidor": plan["planificacion_final"]["factor_competidor"],
        "costo_total_integrado": plan["planificacion_final"]["costo_total_integrado"],
        "estrategia_empresa": plan["planificacion_final"]["estrategia_empresa"],
        "estrategia_competidor": plan["planificacion_final"]["estrategia_competidor"],
        "factible": plan["planificacion_final"]["factible_sin_adquisicion"],
        "ruta": " -> ".join(plan["planificacion_final"]["ruta_nombres"]),
    }]
    _guardar_csv("resultados_planificacion_final.csv",
                 ["algoritmo_origen", "costo_ruta_base", "factor_competidor",
                  "costo_total_integrado", "estrategia_empresa",
                  "estrategia_competidor", "factible", "ruta"],
                 filas_plan)

    # --------------------------------------------------------------
    # 7. Gráficas
    # --------------------------------------------------------------
    nombres_graf = []

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(resumen_heur))
    ancho = 0.35
    ax.bar([i - ancho / 2 for i in x],
           [r["costo_greedy"] or 0 for r in resumen_heur], ancho,
           label="Greedy", color="#f59e0b")
    ax.bar([i + ancho / 2 for i in x],
           [r["costo_astar"] or 0 for r in resumen_heur], ancho,
           label="A*", color="#2563eb")
    ax.set_xticks(list(x))
    ax.set_xticklabels([r["escenario"] for r in resumen_heur])
    ax.set_ylabel("Costo de ruta")
    ax.set_title("Greedy vs A* en tres escenarios")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    img = _procesar_figura(fig, "comparacion_heuristicas.png", para_web)
    if img:
        imagenes["comparacion_heuristicas"] = img
    nombres_graf.append("comparacion_heuristicas.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(1, len(local["ejecuciones"]) + 1),
            [e["costo_inicial"] for e in local["ejecuciones"]],
            "o--", label="Costo inicial", color="#f59e0b")
    ax.plot(range(1, len(local["ejecuciones"]) + 1),
            [e["costo_final"] for e in local["ejecuciones"]],
            "s-", label="Costo final", color="#16a34a")
    ax.set_xlabel("Solución inicial")
    ax.set_ylabel("Costo")
    ax.set_title("Hill Climbing: costo inicial vs final")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    img = _procesar_figura(fig, "busqueda_local.png", para_web)
    if img:
        imagenes["busqueda_local"] = img
    nombres_graf.append("busqueda_local.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    datos_caja = [
        [c["mejor_costo"] for c in sa["corridas"]],
        [c["mejor_costo"] for c in ga["corridas"]],
    ]
    ax.boxplot(datos_caja, tick_labels=["Recocido simulado", "Alg. genético"])
    ax.set_ylabel("Mejor costo por ejecución")
    ax.set_title("Distribución de resultados (20 ejecuciones)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    img = _procesar_figura(fig, "comparacion_metaheuristicas.png", para_web)
    if img:
        imagenes["comparacion_metaheuristicas"] = img
    nombres_graf.append("comparacion_metaheuristicas.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(sa["corridas"][0]["historial_mejor"], label="Recocido simulado",
            color="#7c3aed", linewidth=2)
    ax.plot(ga["corridas"][0]["historial_mejor"], label="Algoritmo genético",
            color="#2563eb", linewidth=2)
    ax.set_xlabel("Iteración / generación")
    ax.set_ylabel("Mejor costo")
    ax.set_title("Convergencia de la primera ejecución")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    img = _procesar_figura(fig, "convergencia_metaheuristicas.png", para_web)
    if img:
        imagenes["convergencia_metaheuristicas"] = img
    nombres_graf.append("convergencia_metaheuristicas.png")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    metodos = ["Minimax", "Alfa-beta"]
    visitados = [minimax_info["sin_poda"]["nodos_visitados"],
                 minimax_info["con_poda"]["nodos_visitados"]]
    podados = [0, minimax_info["con_poda"]["nodos_podados"]]
    ax.bar(metodos, visitados, color="#2563eb", label="Visitados")
    ax.bar(metodos, podados, bottom=visitados, color="#f59e0b",
           label="Podados")
    ax.set_ylabel("Nodos")
    ax.set_title("Minimax vs poda alfa-beta")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    img = _procesar_figura(fig, "minimax_alfabeta.png", para_web)
    if img:
        imagenes["minimax_alfabeta"] = img
    nombres_graf.append("minimax_alfabeta.png")

    resumen = {
        "escenario": escenario.nombre,
        "semilla_base": semilla_base,
        "repeticiones": repeticiones,
        "parametros": parametros,
        "heuristicas": resumen_heur,
        "busqueda_local": {
            "analisis": local["analisis"],
            "mejor": local["mejor"],
            "evaluaciones": local["evaluaciones"],
            "tiempo_total_ms": local["tiempo_total_ms"],
        },
        "recocido_simulado": {k: v for k, v in sa.items() if k != "corridas"},
        "algoritmo_genetico": {k: v for k, v in ga.items() if k != "corridas"},
        "teoria_juegos": {
            "equilibrios_nash": juego["equilibrios_nash"],
            "dominancia": juego["dominancia"],
            "matriz": juego["matriz"],
        },
        "minimax": minimax_info,
        "planificacion_final": plan["planificacion_final"],
        "archivos_csv": [
            "resultados_heuristicas.csv",
            "resumen_heuristicas.csv",
            "resultados_busqueda_local.csv",
            "resultados_metaheuristicas.csv",
            "resumen_metaheuristicas.csv",
            "resultados_teoria_juegos.csv",
            "resultados_minimax.csv",
            "resultados_planificacion_final.csv",
        ],
        "archivo_parametros": "parametros_experimento.json",
        "archivos_graficas": nombres_graf,
        "graficas_base64": imagenes if para_web else {},
        "tiempo_total_ms": round(
            (time.perf_counter() - inicio_total) * 1000.0, 3),
    }
    return resumen


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Ejecutando experimentos reproducibles...")
    resumen = ejecutar_experimentos()
    print("Mejor costo metaheurístico:")
    print("  Recocido simulado:", resumen["recocido_simulado"]["mejor_costo"])
    print("  Algoritmo genético:", resumen["algoritmo_genético"]["mejor_costo"])
    print("CSV en:", DIR_RESULTADOS)
    print("Gráficas en:", DIR_GRAFICAS)