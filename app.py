# -*- coding: utf-8 -*-
"""
Sistema inteligente de planificación, optimización y toma de decisiones
adversarias para una red logística 12 x 12.

Servidor Flask que integra:
  - Escenario logístico configurable (JSON/CSV).
  - Módulo A: Greedy Best-First y A*.
  - Módulo B: Hill Climbing.
  - Módulo C: recocido simulado y algoritmo genético.
  - Módulo D: teoría de juegos.
  - Módulo E: Minimax y poda alfa-beta.
  - Experimentos reproducibles y planificación final integrada.

Ejecutar con:
    python app.py

Abrir en el navegador:
    http://127.0.0.1:5000
"""

from __future__ import annotations

import io
import json
import sys
import threading
import traceback

from flask import (Flask, Response, jsonify, render_template, request,
                   send_file)

from algoritmos.algoritmo_genetico import algoritmo_genetico
from algoritmos.busqueda_heuristica import comparar_greedy_a_estrella
from algoritmos.busqueda_local import hill_climbing
from algoritmos.minimax import comparar_minimax_alfa_beta, minimax, minimax_alfa_beta
from algoritmos.recocido_simulado import recocido_simulado
from algoritmos.teoria_juegos import analizar_juego
from core.costos import construir_matriz_costos, ruta_coordenadas
from core.escenario import Escenario
from core.integracion import (cargar_parametros, ejecutar_planificacion)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

_estado = {"escenario": Escenario.por_defecto()}
_candado = threading.Lock()


# ============================================================
# Utilidades de estado
# ============================================================
def _escenario_actual():
    with _candado:
        return Escenario.desde_dict(_estado["escenario"].to_dict())


def _payload_escenario(escenario):
    errores = escenario.validar()
    return {
        "escenario": escenario.to_dict(),
        "validacion": {"valido": not errores, "errores": errores},
        "puntos_interes": [
            {"nombre": n, "x": x, "y": y}
            for n, x, y in escenario.puntos_interes()
        ],
        "parametros": cargar_parametros(),
    }


def _error(mensaje, codigo=400, detalles=None):
    cuerpo = {"error": mensaje}
    if detalles is not None:
        cuerpo["detalles"] = detalles
    return jsonify(cuerpo), codigo


def _json_body():
    return request.get_json(silent=True) or {}


def _fusionar_parametros(base, extra):
    resultado = json.loads(json.dumps(base))
    for clave, valor in (extra or {}).items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave].update(valor)
        else:
            resultado[clave] = valor
    return resultado


def _ejecutar_recocido(escenario, body):
    datos = construir_matriz_costos(escenario)
    if datos["inalcanzables"]:
        raise ValueError("Hay pares de puntos sin ruta transitable.")
    parametros = cargar_parametros().get("recocido_simulado", {})
    resultado = recocido_simulado(
        datos["matriz"], n_entregas=len(escenario.entregas),
        temperatura_inicial=float(body.get(
            "temperatura_inicial", parametros.get("temperatura_inicial", 50.0))),
        temperatura_final=float(body.get(
            "temperatura_final", parametros.get("temperatura_final", 0.01))),
        factor_enfriamiento=float(body.get(
            "factor_enfriamiento", parametros.get("factor_enfriamiento", 0.97))),
        iteraciones_por_temperatura=int(body.get(
            "iteraciones_por_temperatura",
            parametros.get("iteraciones_por_temperatura", 40))),
        semilla=int(body.get("semilla", 42)))
    resultado["ruta_mejor"] = _nombres_ruta(resultado["mejor_orden"], escenario)
    resultado["puntos"] = _nombres_entregas(escenario)
    resultado["ruta_coordenadas"] = [
        list(c) for c in ruta_coordenadas(
            [i + 1 for i in resultado["mejor_orden"]], datos)]
    return resultado


def _ejecutar_genetico(escenario, body):
    datos = construir_matriz_costos(escenario)
    if datos["inalcanzables"]:
        raise ValueError("Hay pares de puntos sin ruta transitable.")
    parametros = cargar_parametros().get("algoritmo_genetico", {})
    resultado = algoritmo_genetico(
        datos["matriz"], n_entregas=len(escenario.entregas),
        tamano_poblacion=int(body.get(
            "tamano_poblacion", parametros.get("tamano_poblacion", 60))),
        generaciones=int(body.get(
            "generaciones", parametros.get("generaciones", 150))),
        prob_mutacion=float(body.get(
            "prob_mutacion", parametros.get("prob_mutacion", 0.15))),
        prob_cruce=float(body.get(
            "prob_cruce", parametros.get("prob_cruce", 0.9))),
        tamanio_torneo=int(body.get(
            "tamanio_torneo", parametros.get("tamanio_torneo", 3))),
        elitismo=bool(body.get("elitismo", parametros.get("elitismo", True))),
        semilla=int(body.get("semilla", 42)))
    resultado["ruta_mejor"] = _nombres_ruta(resultado["mejor_orden"], escenario)
    resultado["puntos"] = _nombres_entregas(escenario)
    resultado["ruta_coordenadas"] = [
        list(c) for c in ruta_coordenadas(
            [i + 1 for i in resultado["mejor_orden"]], datos)]
    return resultado


# ============================================================
# Interfaz
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.errorhandler(413)
def demasiado_grande(_):
    return _error("El archivo supera el límite de 8 MB.", 413)


@app.errorhandler(Exception)
def error_no_controlado(exc):
    if isinstance(exc, ValueError):
        return _error(str(exc), 400)
    traceback.print_exc()
    return _error("Error interno del servidor: {}".format(exc), 500)


# ============================================================
# Escenario
# ============================================================
@app.route("/api/escenario", methods=["GET"])
def api_obtener_escenario():
    return jsonify(_payload_escenario(_escenario_actual()))


@app.route("/api/escenario", methods=["POST"])
def api_actualizar_escenario():
    datos = _json_body()
    crudo = datos.get("escenario", datos)
    try:
        escenario = Escenario.desde_dict(crudo)
    except (TypeError, ValueError, KeyError) as exc:
        return _error("Escenario inválido: {}".format(exc), 400)

    errores = escenario.validar()
    if errores:
        return _error("El escenario contiene errores.", 400, errores)

    with _candado:
        _estado["escenario"] = escenario
    return jsonify(_payload_escenario(escenario))


@app.route("/api/escenario/validar", methods=["POST"])
def api_validar_escenario():
    datos = _json_body()
    crudo = datos.get("escenario", datos)
    try:
        escenario = Escenario.desde_dict(crudo)
        errores = escenario.validar()
    except (TypeError, ValueError, KeyError) as exc:
        return jsonify({"valido": False, "errores": [str(exc)]})
    return jsonify({"valido": not errores, "errores": errores})


@app.route("/api/escenario/restablecer", methods=["POST"])
@app.route("/restablecer", methods=["POST"])
def api_restablecer():
    escenario = Escenario.por_defecto()
    with _candado:
        _estado["escenario"] = escenario
    return jsonify(_payload_escenario(escenario))


@app.route("/api/escenario/cargar", methods=["POST"])
def api_cargar_escenario():
    archivo = request.files.get("archivo")
    if archivo is None or archivo.filename == "":
        return _error("Debes seleccionar un archivo JSON o CSV.")

    nombre = archivo.filename.lower()
    try:
        contenido = archivo.read().decode("utf-8-sig")
        if nombre.endswith(".json"):
            escenario = Escenario.desde_dict(json.loads(contenido))
        elif nombre.endswith(".csv"):
            escenario = Escenario.desde_csv_texto(
                contenido, nombre=archivo.filename, semilla=42)
        else:
            return _error("Formato no soportado. Usa .json o .csv.")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
        return _error("No se pudo leer el archivo: {}".format(exc))

    errores = escenario.validar()
    if errores:
        return _error("El archivo contiene un escenario inválido.", 400, errores)

    with _candado:
        _estado["escenario"] = escenario
    return jsonify(_payload_escenario(escenario))


@app.route("/api/escenario/exportar/<formato>", methods=["GET"])
def api_exportar_escenario(formato):
    escenario = _escenario_actual()
    if formato == "json":
        datos = json.dumps(escenario.to_dict(), ensure_ascii=False, indent=2)
        return Response(
            datos, mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=escenario.json"})
    if formato == "csv":
        return Response(
            escenario.to_csv_text(), mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=escenario.csv"})
    return _error("Formato no soportado. Usa json o csv.")


# ============================================================
# Módulo A: búsqueda heurística
# ============================================================
@app.route("/api/busqueda_heuristica", methods=["POST"])
def api_busqueda_heuristica():
    escenario = _escenario_actual()
    body = _json_body()
    inicio = tuple(body.get("inicio", escenario.inicio))
    destino = tuple(body.get("destino", escenario.destino))
    if not escenario.mapa.en_limites(*inicio) or not escenario.mapa.en_limites(*destino):
        return _error("Inicio o destino fuera de la cuadrícula.")

    resultado = comparar_greedy_a_estrella(escenario.mapa, inicio, destino)
    resultado["escenario"] = escenario.nombre
    resultado["puntos_interes"] = [
        {"nombre": n, "x": x, "y": y} for n, x, y in escenario.puntos_interes()]
    return jsonify(resultado)


# ============================================================
# Módulo B: búsqueda local
# ============================================================
@app.route("/api/busqueda_local", methods=["POST"])
def api_busqueda_local():
    escenario = _escenario_actual()
    errores = escenario.validar()
    if errores:
        return _error("Escenario inválido.", 400, errores)

    body = _json_body()
    datos = construir_matriz_costos(escenario)
    if datos["inalcanzables"]:
        return _error("Hay pares de puntos sin ruta transitable.")

    resultado = hill_climbing(
        datos["matriz"], n_entregas=len(escenario.entregas),
        soluciones_iniciales=int(body.get("soluciones_iniciales", 10)),
        max_iteraciones=int(body.get("max_iteraciones", 200)),
        semilla=int(body.get("semilla", cargar_parametros().get("semilla_global", 42))))
    resultado["puntos"] = _nombres_entregas(escenario)
    resultado["ruta_mejor"] = _nombres_ruta(resultado["mejor"]["orden"], escenario)
    resultado["ruta_coordenadas"] = [
        list(c) for c in ruta_coordenadas(
            [i + 1 for i in resultado["mejor"]["orden"]], datos)]
    return jsonify(resultado)


# ============================================================
# Módulo C: metaheurísticas
# ============================================================
@app.route("/api/recocido", methods=["POST"])
def api_recocido():
    escenario = _escenario_actual()
    return jsonify(_ejecutar_recocido(escenario, _json_body()))


@app.route("/api/genetico", methods=["POST"])
def api_genetico():
    escenario = _escenario_actual()
    return jsonify(_ejecutar_genetico(escenario, _json_body()))


@app.route("/api/metaheuristicas", methods=["POST"])
def api_metaheuristicas():
    escenario = _escenario_actual()
    body = _json_body()
    return jsonify({
        "recocido_simulado": _ejecutar_recocido(escenario, body),
        "algoritmo_genetico": _ejecutar_genetico(escenario, body),
    })


# ============================================================
# Módulo D: teoría de juegos
# ============================================================
@app.route("/api/teoria_juegos", methods=["POST"])
def api_teoria_juegos():
    escenario = _escenario_actual()
    comparacion = comparar_greedy_a_estrella(
        escenario.mapa, escenario.inicio, escenario.destino)
    if not comparacion["a_estrella"]["encontrado"]:
        return _error("No hay ruta entre Inicio y Destino para valorar el juego.")
    juego = analizar_juego(
        escenario, comparacion["a_estrella"]["costo"] or 1.0)
    return jsonify(juego)


# ============================================================
# Módulo E: Minimax y poda alfa-beta
# ============================================================
@app.route("/api/minimax", methods=["POST"])
def api_minimax():
    escenario = _escenario_actual()
    body = _json_body()
    profundidad = body.get("profundidad")
    if profundidad is not None:
        profundidad = int(profundidad)
    resultado = comparar_minimax_alfa_beta(escenario, profundidad)
    return jsonify(resultado)


@app.route("/api/minimax/solo", methods=["POST"])
def api_minimax_solo():
    escenario = _escenario_actual()
    body = _json_body()
    profundidad = body.get("profundidad")
    if profundidad is not None:
        profundidad = int(profundidad)
    if body.get("usar_poda", False):
        return jsonify(minimax_alfa_beta(escenario, profundidad))
    return jsonify(minimax(escenario, profundidad))


# ============================================================
# Integración y planificación final
# ============================================================
@app.route("/api/integracion", methods=["POST"])
def api_integracion():
    escenario = _escenario_actual()
    parametros = _fusionar_parametros(
        cargar_parametros(), _json_body().get("parametros", {}))
    resultado = ejecutar_planificacion(escenario, parametros)
    return jsonify(resultado)


@app.route("/api/planificacion", methods=["POST"])
@app.route("/ejecutar", methods=["POST", "GET"])
def api_planificacion():
    return api_integracion()


# ============================================================
# Experimentos
# ============================================================
@app.route("/api/experimentos", methods=["POST"])
def api_experimentos():
    from experimentos.ejecutar_experimentos import ejecutar_experimentos

    escenario = _escenario_actual()
    body = _json_body()
    repeticiones = max(1, min(int(body.get("repeticiones", 20)), 100))
    semilla_base = int(body.get("semilla", 42))
    resumen = ejecutar_experimentos(
        escenario, repeticiones=repeticiones, semilla_base=semilla_base,
        parametros=cargar_parametros(), para_web=True)
    return jsonify(resumen)


@app.route("/api/experimentos/archivos", methods=["GET"])
def api_experimentos_archivos():
    import os
    raiz = os.path.dirname(os.path.abspath(__file__))
    listado = {"resultados": [], "graficas": []}
    for carpeta, clave in (("resultados", "resultados"), ("graficas", "graficas")):
        ruta = os.path.join(raiz, "experimentos", carpeta)
        if os.path.isdir(ruta):
            for nombre in sorted(os.listdir(ruta)):
                completo = os.path.join(ruta, nombre)
                if os.path.isfile(completo):
                    listado[clave].append({
                        "nombre": nombre,
                        "bytes": os.path.getsize(completo),
                    })
    return jsonify(listado)


# ============================================================
# Compatibilidad con el Proyecto 5
# ============================================================
@app.route("/puntos", methods=["GET"])
def api_puntos_compatibilidad():
    escenario = _escenario_actual()
    puntos = [
        {"nombre": n, "x": float(x), "y": float(y)}
        for n, x, y in escenario.puntos_interes()
    ]
    datos = construir_matriz_costos(escenario)
    matriz = [
        [None if v == float("inf") else round(float(v), 2) for v in fila]
        for fila in datos["matriz"]
    ]
    return jsonify({
        "puntos": puntos,
        "nombres": [p["nombre"] for p in puntos],
        "num_destinos": len(escenario.entregas),
        "matriz": matriz,
    })


# ============================================================
# Utilidades internas
# ============================================================
def _nombres_entregas(escenario):
    return [e.nombre for e in escenario.entregas]


def _nombres_ruta(orden, escenario):
    nombres = ["Inicio"] + [escenario.entregas[i].nombre for i in orden] + ["Destino"]
    return " -> ".join(nombres)


def main():
    print()
    print("=" * 64)
    print("SISTEMA INTELIGENTE DE PLANIFICACIÓN LOGÍSTICA")
    print("Búsqueda heurística, búsqueda local, metaheurísticas,")
    print("teoría de juegos y decisiones adversarias")
    print("=" * 64)
    escenario = _escenario_actual()
    errores = escenario.validar()
    if errores:
        print("ADVERTENCIA: el escenario tiene errores:")
        for error in errores:
            print("  -", error)
    else:
        print("Escenario válido:", escenario.nombre)
        print("Cuadrícula: {} x {}".format(escenario.filas, escenario.columnas))
        print("Entregas:", len(escenario.entregas))
    print()
    print("Servidor disponible en: http://127.0.0.1:5000")
    print("Presione CTRL+C para detener.")
    print("=" * 64)
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
