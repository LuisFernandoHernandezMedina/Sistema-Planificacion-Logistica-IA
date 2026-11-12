# -*- coding: utf-8 -*-
"""
PROYECTO 5: SISTEMA DE OPTIMIZACIÓN DE RUTAS DE DISTRIBUCIÓN
============================================================
Algoritmo Genético para encontrar una ruta de distribución eficiente
que parta de "Inicio", visite exactamente los destinos definidos una
sola vez cada uno y regrese a "Inicio", minimizando la distancia total.

Los puntos son DINÁMICOS: la interfaz web puede agregar, editar,
eliminar o arrastrar puntos, y el algoritmo utiliza siempre los puntos
actuales (no coordenadas escritas dentro del algoritmo).

Este módulo contiene TODA la lógica del algoritmo genético y la
generación de las gráficas. Es utilizado tanto desde consola
(ejecutando este archivo directamente) como desde la interfaz web
(importado por app.py).
"""

import io
import sys
import math
import base64
import random

# Asegurar que la consola de Windows muestre correctamente los acentos.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import matplotlib

# Backend "Agg": permite generar las gráficas sin abrir ventanas,
# lo que es ideal para el servidor web de Flask.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ============================================================
# 1. DATOS DEL PROBLEMA (configuración original por defecto)
# ============================================================
# El índice 0 corresponde al punto de partida "Inicio".
# Los índices 1..10 corresponden a los destinos D1..D10.
PUNTOS_ORIGINALES = [
    (0, 0),    # 0  -> Inicio
    (2, 4),    # 1  -> D1
    (5, 2),    # 2  -> D2
    (1, 7),    # 3  -> D3
    (8, 3),    # 4  -> D4
    (6, 8),    # 5  -> D5
    (3, 6),    # 6  -> D6
    (9, 7),    # 7  -> D7
    (4, 10),   # 8  -> D8
    (10, 4),   # 9  -> D9
    (7, 1),    # 10 -> D10
]

NOMBRES_ORIGINALES = ["Inicio"] + ["D{}".format(i) for i in range(1, 11)]

# Aliases para compatibilidad con versiones anteriores.
PUNTOS = PUNTOS_ORIGINALES
ETIQUETAS = NOMBRES_ORIGINALES

# Parámetros por defecto del algoritmo.
TAMANO_POBLACION = 100
GENERACIONES = 500
PROB_MUTACION = 0.10
TAMANIO_TORNEO = 3
SEMILLA = 42


# ============================================================
# 2. MATRIZ DE DISTANCIAS (construida por código)
# ============================================================
def construir_matriz_distancias(puntos):
    """
    Construye la matriz de distancias euclidianas entre TODOS los
    puntos (Inicio + destinos). Los valores NO se escriben a mano:
    se calculan con la fórmula de distancia euclidiana.

        d = sqrt((x2 - x1)^2 + (y2 - y1)^2)
    """
    n = len(puntos)
    matriz = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            dx = puntos[i][0] - puntos[j][0]
            dy = puntos[i][1] - puntos[j][1]
            matriz[i][j] = math.sqrt(dx * dx + dy * dy)
    return matriz


# Matriz por defecto (configuración original).
matriz_distancias = construir_matriz_distancias(PUNTOS_ORIGINALES)


# ============================================================
# 3. REPRESENTACIÓN Y UTILIDADES DE RUTAS
# ============================================================
def ruta_con_inicio(ruta):
    """
    Convierte una permutación de destinos [d, d, ...] en la ruta
    completa que empieza y termina en Inicio (índice 0).
    """
    return [0] + list(ruta) + [0]


def ruta_a_nombres(ruta, etiquetas=None):
    """Devuelve la ruta como lista de nombres legibles."""
    if etiquetas is None:
        etiquetas = ETIQUETAS
    return [etiquetas[i] for i in ruta_con_inicio(ruta)]


def ruta_a_texto(ruta, etiquetas=None):
    """Devuelve la ruta como una cadena: Inicio -> D1 -> ... -> Inicio."""
    return " -> ".join(ruta_a_nombres(ruta, etiquetas))


def distancia_ruta(ruta, matriz=None):
    """
    Distancia total de una ruta. La ruta recibida es una permutación
    de destinos (1..n); internamente se añade Inicio al principio y
    al final.
    """
    if matriz is None:
        matriz = matriz_distancias
    total = float(matriz[0][ruta[0]])
    for i in range(len(ruta) - 1):
        total += float(matriz[ruta[i]][ruta[i + 1]])
    total += float(matriz[ruta[-1]][0])
    return total


def aptitud(ruta, matriz=None):
    """
    Función de aptitud: menor distancia = mejor solución. Se usa el
    inverso de la distancia para que un valor mayor sea mejor.
    """
    return 1.0 / distancia_ruta(ruta, matriz)


def validar_ruta(ruta, destinos=None):
    """
    Comprueba que una ruta sea válida:
      - contiene exactamente los destinos esperados,
      - no hay destinos repetidos,
      - no falta ningún destino.
    Devuelve True si es válida.
    """
    if destinos is None:
        destinos = list(range(1, len(PUNTOS_ORIGINALES)))
    return sorted(ruta) == sorted(destinos)


# ============================================================
# 4. POBLACIÓN INICIAL
# ============================================================
def generar_poblacion(tamano=TAMANO_POBLACION, destinos=None):
    """
    Genera `tamano` rutas aleatorias. Cada ruta es una permutación
    de los destinos, por lo que nunca hay repetidos ni faltantes.
    """
    if destinos is None:
        destinos = list(range(1, len(PUNTOS_ORIGINALES)))
    return [random.sample(destinos, len(destinos)) for _ in range(tamano)]


# ============================================================
# 5. SELECCIÓN POR TORNEO
# ============================================================
def seleccion_torneo(poblacion, matriz=None, tamanio_torneo=TAMANIO_TORNEO,
                     rng=None):
    """
    Selección por torneo:
      1. Se eligen `tamanio_torneo` individuos al azar.
      2. Gana el que tenga MENOR distancia total (mejor aptitud).
      3. Se devuelve una copia del ganador como padre/madre.

    Cuanto mayor sea el tamaño del torneo, mayor presión selectiva.
    """
    if rng is None:
        rng = random
    participantes = rng.sample(poblacion, tamanio_torneo)
    mejor = min(participantes, key=lambda ind: distancia_ruta(ind, matriz))
    return mejor[:]


# ============================================================
# 6. CRUZAMIENTO ORDER CROSSOVER (OX)
# ============================================================
def cruzamiento_ox(padre1, padre2, rng=None):
    """
    Order Crossover (OX) para permutaciones.

    Procedimiento:
      1. Se eligen dos puntos de corte a y b.
      2. El segmento [a, b] del padre1 se copia tal cual al hijo.
      3. Los genes restantes se toman del padre2 en orden circular
         (empezando después de b), saltando los que ya están en el
         segmento copiado.
      4. Se rellenan las posiciones vacías del hijo.

    Garantiza rutas válidas: no hay destinos repetidos ni faltantes.
    Como Inicio (0) no forma parte de la permutación, permanece al
    principio y al final de la ruta completa.
    """
    if rng is None:
        rng = random
    n = len(padre1)
    a, b = sorted(rng.sample(range(n), 2))

    hijo = [None] * n
    # Paso 2: copiar el segmento del padre1.
    hijo[a:b + 1] = padre1[a:b + 1]

    # Paso 3: recorrer el padre2 en orden circular desde b+1.
    orden_padre2 = padre2[b + 1:] + padre2[:b + 1]

    # Paso 4: rellenar posiciones vacías con genes no usados.
    idx = 0
    for i in range(n):
        if hijo[i] is None:
            while orden_padre2[idx] in hijo:
                idx += 1
            hijo[i] = orden_padre2[idx]
            idx += 1

    return hijo


# ============================================================
# 7. MUTACIÓN POR INTERCAMBIO (SWAP MUTATION)
# ============================================================
def mutar(ruta, prob_mutacion=PROB_MUTACION, rng=None):
    """
    Swap Mutation: con probabilidad `prob_mutacion` se seleccionan
    dos destinos al azar y se intercambian sus posiciones.

    Como Inicio no forma parte de la permutación, nunca se modifica.
    """
    if rng is None:
        rng = random
    ruta = ruta[:]
    if len(ruta) >= 2 and rng.random() < prob_mutacion:
        i, j = rng.sample(range(len(ruta)), 2)
        ruta[i], ruta[j] = ruta[j], ruta[i]
    return ruta


# ============================================================
# 8. ALGORITMO GENÉTICO COMPLETO
# ============================================================
def ejecutar_algoritmo(puntos=None,
                       nombres=None,
                       tamano_poblacion=TAMANO_POBLACION,
                       generaciones=GENERACIONES,
                       prob_mutacion=PROB_MUTACION,
                       tamanio_torneo=TAMANIO_TORNEO,
                       verbose=True):
    """
    Ejecuta el algoritmo genético completo usando los puntos actuales
    y devuelve un diccionario con todos los resultados.

    Parámetros:
      - puntos: lista de tuplas (x, y). El primer elemento es Inicio.
      - nombres: lista de nombres de los puntos (paralela a `puntos`).

    Salida (dict):
      - ruta_inicial / distancia_inicial
      - mejor_ruta / distancia_final
      - historial_mejor_distancia
      - mejora_porcentaje
      - generaciones, tamano_poblacion, prob_mutacion
    """
    # Usar la configuración original si no se entregan puntos.
    if puntos is None:
        puntos = list(PUNTOS_ORIGINALES)
    if nombres is None:
        nombres = list(NOMBRES_ORIGINALES)

    puntos = [tuple(p) for p in puntos]
    nombres = list(nombres)

    if len(puntos) < 2:
        raise ValueError("Se necesita Inicio y al menos un destino.")

    # Matriz de distancias construida a partir de los puntos actuales.
    matriz = construir_matriz_distancias(puntos)
    destinos = list(range(1, len(puntos)))

    # Semilla fija para reproducir los resultados.
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)

    # Ruta inicial de referencia (orden natural de los destinos).
    ruta_inicial = destinos[:]
    distancia_inicial = distancia_ruta(ruta_inicial, matriz)

    # Población inicial de 100 rutas aleatorias.
    poblacion = generar_poblacion(tamano_poblacion, destinos)

    historial_mejor_distancia = []
    mejor_global = None
    mejor_global_dist = float("inf")

    if verbose:
        print("=" * 40)
        print("SISTEMA DE OPTIMIZACIÓN DE RUTAS")
        print("=" * 40)
        print()
        print("Población: {}".format(tamano_poblacion))
        print("Generaciones: {}".format(generaciones))
        print("Mutación: {}%".format(int(prob_mutacion * 100)))
        print("Destinos: {}".format(len(destinos)))
        print()
        print("Ruta inicial:")
        print(ruta_a_texto(ruta_inicial, nombres))
        print()
        print("Distancia inicial:")
        print("{:.2f}".format(distancia_inicial))
        print()

    # Bucle evolutivo: de la generación 0 a la `generaciones`.
    for gen in range(generaciones + 1):
        # Evaluar aptitud de toda la población.
        distancias = [distancia_ruta(ind, matriz) for ind in poblacion]
        mejor_idx = min(range(len(poblacion)), key=lambda k: distancias[k])

        # Actualizar la mejor solución global (elitismo acumulado).
        if distancias[mejor_idx] < mejor_global_dist:
            mejor_global_dist = distancias[mejor_idx]
            mejor_global = poblacion[mejor_idx][:]

        # Registrar la evolución de la mejor distancia.
        historial_mejor_distancia.append(mejor_global_dist)

        # Mostrar progreso en consola cada 50 generaciones.
        if verbose and (gen % 50 == 0 or gen == generaciones):
            print("Generación {}: {:.2f} km".format(gen, mejor_global_dist))

        # La última iteración solo registra; no genera descendencia.
        if gen == generaciones:
            break

        # --- Construcción de la nueva población ---
        # Elitismo: el mejor individuo pasa directamente a la siguiente.
        nueva_poblacion = [mejor_global[:]]

        while len(nueva_poblacion) < tamano_poblacion:
            padre1 = seleccion_torneo(poblacion, matriz, tamanio_torneo)
            padre2 = seleccion_torneo(poblacion, matriz, tamanio_torneo)
            hijo = cruzamiento_ox(padre1, padre2)
            hijo = mutar(hijo, prob_mutacion)
            nueva_poblacion.append(hijo)

        poblacion = nueva_poblacion

    # Cálculo del porcentaje de mejora.
    if distancia_inicial > 0:
        mejora_porcentaje = ((distancia_inicial - mejor_global_dist)
                             / distancia_inicial) * 100.0
    else:
        mejora_porcentaje = 0.0

    if verbose:
        print()
        print("Mejor solución encontrada:")
        print(ruta_a_texto(mejor_global, nombres))
        print()
        print("Distancia final:")
        print("{:.2f}".format(mejor_global_dist))
        print()
        print("Mejora:")
        print("{:.2f}%".format(mejora_porcentaje))
        print()

    return {
        "ruta_inicial": ruta_a_nombres(ruta_inicial, nombres),
        "ruta_inicial_texto": ruta_a_texto(ruta_inicial, nombres),
        "ruta_inicial_indices": ruta_inicial,
        "distancia_inicial": distancia_inicial,
        "mejor_ruta": ruta_a_nombres(mejor_global, nombres),
        "mejor_ruta_texto": ruta_a_texto(mejor_global, nombres),
        "mejor_ruta_indices": mejor_global,
        "distancia_final": mejor_global_dist,
        "historial_mejor_distancia": historial_mejor_distancia,
        "mejora_porcentaje": mejora_porcentaje,
        "generaciones": generaciones,
        "tamano_poblacion": tamano_poblacion,
        "prob_mutacion": prob_mutacion,
    }


# ============================================================
# 9. GRÁFICAS (se convierten a Base64 para la interfaz web)
# ============================================================
def _figura_a_base64(fig):
    """Convierte una figura de Matplotlib a una cadena Base64 PNG."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    buffer.seek(0)
    imagen = base64.b64encode(buffer.read()).decode("utf-8")
    plt.close(fig)
    return imagen


def grafica_evolucion(historial):
    """
    Gráfica de la evolución de la mejor solución.
    Eje X = Generación, Eje Y = Distancia total.
    Devuelve una imagen PNG en Base64.
    """
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(len(historial)), historial, color="#2563eb", linewidth=2)
    ax.set_title("Evolución de la mejor solución", fontsize=13, fontweight="bold")
    ax.set_xlabel("Generación")
    ax.set_ylabel("Distancia total")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    return _figura_a_base64(fig)


def grafica_ruta(ruta, puntos=None, etiquetas=None):
    """
    Gráfica de la ruta final. Recibe la ruta completa (con Inicio al
    principio y al final) o una permutación de destinos.
    Dibuja los puntos, las líneas que los conectan en orden, las
    etiquetas, título y ejes.
    Devuelve una imagen PNG en Base64.
    """
    if puntos is None:
        puntos = PUNTOS_ORIGINALES
    if etiquetas is None:
        etiquetas = NOMBRES_ORIGINALES

    completa = ruta if (ruta and ruta[0] == 0) else ruta_con_inicio(ruta)

    xs = [puntos[i][0] for i in completa]
    ys = [puntos[i][1] for i in completa]

    fig, ax = plt.subplots(figsize=(7, 6))
    # Líneas de la ruta (cerrando el circuito en Inicio).
    ax.plot(xs, ys, color="#64748b", linewidth=1.8, zorder=1)

    # Destinos.
    dx = [puntos[i][0] for i in completa[1:-1]]
    dy = [puntos[i][1] for i in completa[1:-1]]
    ax.scatter(dx, dy, color="#2563eb", s=70, zorder=2, label="Destinos")

    # Inicio.
    ax.scatter([puntos[0][0]], [puntos[0][1]], color="#16a34a",
               s=140, marker="*", zorder=3, label="Inicio")

    # Etiquetas de cada punto.
    for i in set(completa):
        ax.annotate(etiquetas[i], (puntos[i][0], puntos[i][1]),
                    textcoords="offset points", xytext=(7, 5), fontsize=9)

    ax.set_title("Ruta optimizada encontrada", fontsize=13, fontweight="bold")
    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="best")
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    return _figura_a_base64(fig)


# ============================================================
# 10. EJECUCIÓN DIRECTA EN CONSOLA
# ============================================================
if __name__ == "__main__":
    resultado = ejecutar_algoritmo(verbose=True)

    # Validación de la solución final.
    assert validar_ruta(resultado["mejor_ruta_indices"],
                        list(range(1, len(PUNTOS_ORIGINALES)))), \
        "La mejor ruta no es válida"

    # Generar y guardar las gráficas localmente como archivos PNG.
    imagen_evo = grafica_evolucion(resultado["historial_mejor_distancia"])
    imagen_ruta = grafica_ruta(resultado["mejor_ruta_indices"])

    with open("evolucion.png", "wb") as f:
        f.write(base64.b64decode(imagen_evo))
    with open("ruta_optimizada.png", "wb") as f:
        f.write(base64.b64decode(imagen_ruta))

    print("Gráficas guardadas: evolucion.png y ruta_optimizada.png")
