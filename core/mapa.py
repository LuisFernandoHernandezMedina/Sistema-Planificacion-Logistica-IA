# -*- coding: utf-8 -*-
"""
Cuadrícula logística 12 x 12.

Cada celda tiene:
  - un costo de desplazamiento (entrar a la celda cuesta ese valor),
  - o es un obstáculo intransitable.

Convención de coordenadas:
  x = columna (0 .. columnas-1)
  y = fila    (0 .. filas-1)

Movimientos permitidos: arriba, abajo, izquierda, derecha (4 vecinos).
No se permiten diagonales para que la distancia Manhattan sea una cota
inferior válida del número de pasos.
"""

from __future__ import annotations

OBSTACULO = "#"


class Mapa:
    """Representa la cuadrícula, sus costos y sus obstáculos."""

    def __init__(self, filas=12, columnas=12, costos=None, obstaculos=None):
        self.filas = int(filas)
        self.columnas = int(columnas)
        if self.filas < 2 or self.columnas < 2:
            raise ValueError("La cuadrícula debe tener al menos 2 x 2 celdas.")

        if costos is None:
            costos = [[1.0 for _ in range(self.columnas)]
                      for _ in range(self.filas)]
        if len(costos) != self.filas:
            raise ValueError("El número de filas de costos no coincide.")
        for fila in costos:
            if len(fila) != self.columnas:
                raise ValueError("El número de columnas de costos no coincide.")

        self.costos = [[self._costo_valido(v) for v in fila] for fila in costos]
        self.obstaculos = set()
        for punto in (obstaculos or []):
            x, y = int(punto[0]), int(punto[1])
            if not self.en_limites(x, y):
                raise ValueError(
                    "Obstáculo fuera de la cuadrícula: ({}, {}).".format(x, y))
            self.obstaculos.add((x, y))

    # ------------------------------------------------------------------
    # Validaciones y consultas básicas
    # ------------------------------------------------------------------
    @staticmethod
    def _costo_valido(valor):
        try:
            costo = float(valor)
        except (TypeError, ValueError):
            raise ValueError("Costo de celda no numérico: {!r}".format(valor))
        if costo <= 0:
            raise ValueError("Los costos de desplazamiento deben ser > 0.")
        return costo

    def en_limites(self, x, y):
        return 0 <= int(x) < self.columnas and 0 <= int(y) < self.filas

    def es_transitable(self, x, y):
        return self.en_limites(x, y) and (int(x), int(y)) not in self.obstaculos

    def costo(self, x, y):
        """Costo de entrar a la celda (x, y)."""
        if not self.en_limites(x, y):
            raise ValueError("Celda fuera de la cuadrícula: ({}, {}).".format(x, y))
        return self.costos[int(y)][int(x)]

    def costo_minimo(self):
        """Menor costo de una celda transitable (cota para la heurística)."""
        valores = [
            self.costos[y][x]
            for y in range(self.filas)
            for x in range(self.columnas)
            if (x, y) not in self.obstaculos
        ]
        return min(valores) if valores else 1.0

    def vecinos(self, x, y):
        """Devuelve los vecinos transitables en las cuatro direcciones."""
        x, y = int(x), int(y)
        candidatos = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [(nx, ny) for nx, ny in candidatos if self.es_transitable(nx, ny)]

    def es_obstaculo(self, x, y):
        return (int(x), int(y)) in self.obstaculos

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "filas": self.filas,
            "columnas": self.columnas,
            "costos": [[round(float(v), 2) for v in fila] for fila in self.costos],
            "obstaculos": sorted([[x, y] for x, y in self.obstaculos]),
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(
            filas=datos.get("filas", len(datos.get("costos", []))),
            columnas=datos.get("columnas", 12),
            costos=datos.get("costos"),
            obstaculos=datos.get("obstaculos"),
        )

    def to_csv_text(self):
        """Exporta la cuadrícula como CSV; '#' representa un obstáculo."""
        lineas = []
        for y in range(self.filas):
            fila = []
            for x in range(self.columnas):
                if (x, y) in self.obstaculos:
                    fila.append(OBSTACULO)
                else:
                    fila.append(self._formato_numero(self.costos[y][x]))
            lineas.append(",".join(fila))
        return "\n".join(lineas) + "\n"

    @staticmethod
    def _formato_numero(valor):
        if float(valor).is_integer():
            return str(int(valor))
        return "{:.2f}".format(float(valor))

    @classmethod
    def desde_csv_texto(cls, texto):
        """Carga una cuadrícula desde texto CSV con números y '#'."""
        texto = texto.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        lineas = [line for line in texto.split("\n") if line.strip() != ""]
        if not lineas:
            raise ValueError("El CSV del mapa está vacío.")

        matriz = []
        obstaculos = []
        for y, linea in enumerate(lineas):
            celdas = [c.strip() for c in linea.replace(";", ",").split(",")]
            fila = []
            for x, celda in enumerate(celdas):
                if celda in ("#", "X", "x"):
                    fila.append(1.0)
                    obstaculos.append([x, y])
                else:
                    fila.append(float(celda))
            matriz.append(fila)

        return cls(filas=len(matriz), columnas=len(matriz[0]),
                   costos=matriz, obstaculos=obstaculos)
