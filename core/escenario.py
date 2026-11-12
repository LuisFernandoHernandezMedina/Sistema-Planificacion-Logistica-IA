# -*- coding: utf-8 -*-
"""
Escenario logístico compartido por los cinco módulos.

Contiene la cuadrícula, el inicio, el destino final, las entregas,
los recursos disponibles y la información del competidor.

El escenario puede cargarse desde:
  - JSON completo (config/escenario.json),
  - CSV combinado (una fila por celda con tipo, punto, costo y recursos).
"""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass, field

from .mapa import Mapa


@dataclass
class Entrega:
    """Punto de entrega con demanda y consumo de recursos."""

    id: str
    nombre: str
    x: int
    y: int
    demanda: int = 1
    recursos: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "x": int(self.x),
            "y": int(self.y),
            "demanda": int(self.demanda),
            "recursos": {k: int(v) for k, v in self.recursos.items()},
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(
            id=str(datos.get("id") or datos.get("nombre", "E")),
            nombre=str(datos.get("nombre", datos.get("id", "Entrega"))),
            x=int(datos.get("x")),
            y=int(datos.get("y")),
            demanda=int(datos.get("demanda", 1)),
            recursos={str(k): int(v) for k, v in (datos.get("recursos") or {}).items()},
        )


class Escenario:
    """Escenario logístico común a todos los módulos."""

    def __init__(self, nombre, filas, columnas, inicio, destino, entregas,
                 mapa, recursos=None, competidor=None, semilla=42):
        self.nombre = str(nombre)
        self.filas = int(filas)
        self.columnas = int(columnas)
        self.inicio = (int(inicio[0]), int(inicio[1]))
        self.destino = (int(destino[0]), int(destino[1]))
        self.entregas = [e if isinstance(e, Entrega) else Entrega.desde_dict(e)
                         for e in entregas]
        self.mapa = mapa if isinstance(mapa, Mapa) else Mapa.desde_dict(mapa)
        self.recursos = {str(k): float(v) for k, v in (recursos or {}).items()}
        self.competidor = dict(competidor or {})
        self.semilla = int(semilla)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def puntos_interes(self):
        """Orden fijo: Inicio, entregas, Destino final."""
        puntos = [("Inicio", self.inicio[0], self.inicio[1])]
        for entrega in self.entregas:
            puntos.append((entrega.nombre, entrega.x, entrega.y))
        puntos.append(("Destino", self.destino[0], self.destino[1]))
        return puntos

    def coordenadas_puntos(self):
        return [(x, y) for _, x, y in self.puntos_interes()]

    def entregas_dict(self):
        return [e.to_dict() for e in self.entregas]

    def recursos_requeridos(self):
        total = {}
        for entrega in self.entregas:
            for clave, valor in entrega.recursos.items():
                total[clave] = total.get(clave, 0) + int(valor)
        return total

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------
    def validar(self):
        """Devuelve una lista de errores; vacía significa escenario válido."""
        errores = []
        if self.mapa.filas != self.filas or self.mapa.columnas != self.columnas:
            errores.append("Las dimensiones del mapa no coinciden con el escenario.")
        if len(self.entregas) < 3:
            errores.append("Se requieren al menos tres puntos de entrega.")

        if not self.mapa.en_limites(*self.inicio):
            errores.append("El inicio está fuera de la cuadrícula.")
        elif not self.mapa.es_transitable(*self.inicio):
            errores.append("El inicio está sobre un obstáculo.")

        if not self.mapa.en_limites(*self.destino):
            errores.append("El destino final está fuera de la cuadrícula.")
        elif not self.mapa.es_transitable(*self.destino):
            errores.append("El destino final está sobre un obstáculo.")

        if self.inicio == self.destino:
            errores.append("El inicio y el destino final deben ser distintos.")

        posiciones = {self.inicio: "Inicio", self.destino: "Destino"}
        ids = set()
        nombres = set()
        for entrega in self.entregas:
            if entrega.id in ids:
                errores.append("Id de entrega repetido: {}.".format(entrega.id))
            if entrega.nombre.lower() in nombres:
                errores.append("Nombre de entrega repetido: {}.".format(entrega.nombre))
            ids.add(entrega.id)
            nombres.add(entrega.nombre.lower())

            if not self.mapa.en_limites(entrega.x, entrega.y):
                errores.append(
                    "La entrega '{}' está fuera de la cuadrícula.".format(entrega.nombre))
                continue
            if not self.mapa.es_transitable(entrega.x, entrega.y):
                errores.append(
                    "La entrega '{}' está sobre un obstáculo.".format(entrega.nombre))
            pos = (entrega.x, entrega.y)
            if pos in posiciones:
                errores.append(
                    "La entrega '{}' comparte celda con {}.".format(
                        entrega.nombre, posiciones[pos]))
            posiciones[pos] = entrega.nombre

            if entrega.demanda <= 0:
                errores.append(
                    "La demanda de '{}' debe ser positiva.".format(entrega.nombre))
            for clave, valor in entrega.recursos.items():
                if valor < 0:
                    errores.append(
                        "Recurso negativo en '{}'.".format(entrega.nombre))
                if clave not in self.recursos:
                    errores.append(
                        "Recurso '{}' no definido en el escenario.".format(clave))

        requeridos = self.recursos_requeridos()
        for clave, valor in requeridos.items():
            disponible = self.recursos.get(clave, 0)
            if valor > disponible:
                errores.append(
                    "Recursos insuficientes de '{}': requiere {}, disponible {}."
                    .format(clave, valor, disponible))

        if not self.mapa.es_transitable(*self.inicio) or \
                not self.mapa.es_transitable(*self.destino):
            pass

        return errores

    def esta_conectado(self, algoritmo_ruta=None):
        """Comprueba que exista una ruta inicio -> destino."""
        if algoritmo_ruta is None:
            from algoritmos.busqueda_heuristica import a_estrella
            algoritmo_ruta = a_estrella
        resultado = algoritmo_ruta(self.mapa, self.inicio, self.destino)
        return bool(resultado.get("encontrado"))

    # ------------------------------------------------------------------
    # Serialización JSON
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "nombre": self.nombre,
            "filas": self.filas,
            "columnas": self.columnas,
            "inicio": list(self.inicio),
            "destino": list(self.destino),
            "entregas": self.entregas_dict(),
            "recursos": {k: v for k, v in self.recursos.items()},
            "competidor": dict(self.competidor),
            "semilla": self.semilla,
            "mapa": self.mapa.to_dict(),
        }

    @classmethod
    def desde_dict(cls, datos):
        mapa_datos = datos.get("mapa") or {}
        filas = int(datos.get("filas", mapa_datos.get("filas", 12)))
        columnas = int(datos.get("columnas", mapa_datos.get("columnas", 12)))
        if not mapa_datos.get("costos"):
            mapa_datos = {
                "filas": filas,
                "columnas": columnas,
                "costos": [[1.0] * columnas for _ in range(filas)],
                "obstaculos": mapa_datos.get("obstaculos", []),
            }
        mapa = Mapa.desde_dict(mapa_datos)
        return cls(
            nombre=datos.get("nombre", "Escenario"),
            filas=filas,
            columnas=columnas,
            inicio=datos.get("inicio", [0, 0]),
            destino=datos.get("destino", [columnas - 1, filas - 1]),
            entregas=datos.get("entregas", []),
            mapa=mapa,
            recursos=datos.get("recursos", {}),
            competidor=datos.get("competidor", {}),
            semilla=datos.get("semilla", 42),
        )

    @classmethod
    def cargar_json(cls, ruta):
        with open(ruta, "r", encoding="utf-8") as archivo:
            return cls.desde_dict(json.load(archivo))

    def guardar_json(self, ruta):
        directorio = os.path.dirname(os.path.abspath(ruta))
        if directorio and not os.path.isdir(directorio):
            os.makedirs(directorio, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(self.to_dict(), archivo, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # CSV combinado: una fila por celda
    # ------------------------------------------------------------------
    CAMPOS_CSV = ["x", "y", "costo", "obstaculo", "tipo", "nombre", "id",
                  "demanda", "recursos", "nombre_escenario", "semilla",
                  "recursos_globales", "competidor", "orden"]

    def to_csv_text(self):
        buffer = io.StringIO()
        escritor = csv.DictWriter(buffer, fieldnames=self.CAMPOS_CSV,
                                  lineterminator="\n")
        escritor.writeheader()

        metadatos = {
            "nombre_escenario": self.nombre,
            "semilla": self.semilla,
            "recursos_globales": ";".join(
                "{}={}".format(k, Mapa._formato_numero(v))
                for k, v in self.recursos.items()),
            "competidor": ";".join(
                "{}={}".format(k, Mapa._formato_numero(v)
                               if isinstance(v, (int, float)) else v)
                for k, v in self.competidor.items()),
        }

        especiales = {}
        especiales[self.inicio] = {"tipo": "inicio", "nombre": "Inicio"}
        especiales[self.destino] = {"tipo": "destino", "nombre": "Destino"}
        for indice, entrega in enumerate(self.entregas):
            especiales[(entrega.x, entrega.y)] = {
                "tipo": "entrega",
                "nombre": entrega.nombre,
                "id": entrega.id,
                "demanda": entrega.demanda,
                "recursos": ";".join(
                    "{}={}".format(k, v) for k, v in entrega.recursos.items()),
                "orden": indice,
            }

        for y in range(self.filas):
            for x in range(self.columnas):
                fila = {campo: "" for campo in self.CAMPOS_CSV}
                fila["x"] = x
                fila["y"] = y
                if (x, y) in self.mapa.obstaculos:
                    fila["obstaculo"] = 1
                    fila["costo"] = ""
                else:
                    fila["costo"] = self.mapa._formato_numero(self.mapa.costo(x, y))
                if (x, y) in especiales:
                    fila.update(especiales[(x, y)])
                if x == 0 and y == 0:
                    fila.update(metadatos)
                escritor.writerow(fila)
        return buffer.getvalue()

    @classmethod
    def desde_csv_texto(cls, texto, nombre="Escenario CSV", semilla=42):
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
        lector = csv.DictReader(io.StringIO(texto))
        if not lector.fieldnames:
            raise ValueError("El CSV no tiene encabezado.")

        filas = {}
        inicio = None
        destino = None
        entregas_con_orden = []
        obstaculos = []
        recursos_fallback = {}
        recursos_globales = None
        competidor = None
        nombre_escenario = nombre
        semilla_final = semilla
        max_x = -1
        max_y = -1

        def _parsear_dict(texto, convertir_float=False):
            resultado = {}
            for parte in str(texto or "").split(";"):
                parte = parte.strip()
                if "=" not in parte:
                    continue
                clave, valor = parte.split("=", 1)
                clave = clave.strip()
                valor = valor.strip()
                if convertir_float:
                    try:
                        resultado[clave] = float(valor)
                    except ValueError:
                        resultado[clave] = valor
                else:
                    resultado[clave] = valor
            return resultado

        def _orden_csv(fila, posicion):
            try:
                return int(float(fila.get("orden")))
            except (TypeError, ValueError):
                return posicion

        for fila in lector:
            try:
                x = int(fila["x"])
                y = int(fila["y"])
            except (KeyError, TypeError, ValueError):
                raise ValueError("Cada fila del CSV debe tener x e y enteros.")
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            if str(fila.get("nombre_escenario", "")).strip():
                nombre_escenario = str(fila.get("nombre_escenario")).strip()
            if str(fila.get("semilla", "")).strip():
                try:
                    semilla_final = int(float(fila.get("semilla")))
                except (TypeError, ValueError):
                    pass
            if str(fila.get("recursos_globales", "")).strip():
                recursos_globales = _parsear_dict(
                    fila.get("recursos_globales"), convertir_float=True)
            if str(fila.get("competidor", "")).strip():
                competidor = _parsear_dict(
                    fila.get("competidor"), convertir_float=True)
            filas[(x, y)] = {
                "costo": fila.get("costo") or 1,
                "obstaculo": str(fila.get("obstaculo", "")).strip() in ("1", "si", "sí", "true", "X", "x", "#"),
            }
            tipo = str(fila.get("tipo", "")).strip().lower()
            if tipo == "inicio":
                inicio = (x, y)
            elif tipo == "destino":
                destino = (x, y)
            elif tipo == "entrega":
                recursos_entrega = {}
                for parte in str(fila.get("recursos") or "").split(";"):
                    parte = parte.strip()
                    if "=" in parte:
                        clave, valor = parte.split("=", 1)
                        recursos_entrega[clave.strip()] = int(valor.strip())
                        recursos_fallback[clave.strip()] = max(
                            recursos_fallback.get(clave.strip(), 0),
                            int(valor.strip()) * 3)
                entregas_con_orden.append((
                    _orden_csv(fila, len(entregas_con_orden)),
                    {
                        "id": str(fila.get("id") or fila.get("nombre") or "E{}".format(len(entregas_con_orden) + 1)),
                        "nombre": str(fila.get("nombre") or "Entrega {}".format(len(entregas_con_orden) + 1)),
                        "x": x,
                        "y": y,
                        "demanda": int(fila.get("demanda") or 1),
                        "recursos": recursos_entrega,
                    },
                ))
            if filas[(x, y)]["obstaculo"]:
                obstaculos.append([x, y])

        if inicio is None or destino is None:
            raise ValueError("El CSV debe marcar un inicio y un destino.")
        if max_x < 1 or max_y < 1:
            raise ValueError("El CSV debe describir una cuadrícula válida.")

        entregas = [datos for _, datos in sorted(
            entregas_con_orden, key=lambda item: item[0])]

        filas_dim = max_y + 1
        columnas_dim = max_x + 1
        costos = [[1.0 for _ in range(columnas_dim)] for _ in range(filas_dim)]
        for (x, y), datos in filas.items():
            if not datos["obstaculo"]:
                costos[y][x] = float(datos["costo"])

        mapa = Mapa(filas=filas_dim, columnas=columnas_dim,
                    costos=costos, obstaculos=obstaculos)
        recursos = recursos_globales if recursos_globales is not None \
            else recursos_fallback
        if competidor is None:
            competidor = {"nombre": "Competidor", "efecto_costo": 1.15,
                          "reduccion_recurso": 0.15, "agresividad": 0.6}
        else:
            competidor.setdefault("nombre", "Competidor")
        return cls(
            nombre=nombre_escenario,
            filas=filas_dim,
            columnas=columnas_dim,
            inicio=inicio,
            destino=destino,
            entregas=entregas,
            mapa=mapa,
            recursos=recursos,
            competidor=competidor,
            semilla=semilla_final,
        )

    @classmethod
    def desde_csv(cls, ruta, nombre=None, semilla=42):
        with open(ruta, "r", encoding="utf-8-sig") as archivo:
            return cls.desde_csv_texto(archivo.read(), nombre or ruta, semilla)

    # ------------------------------------------------------------------
    # Escenario por defecto
    # ------------------------------------------------------------------
    @classmethod
    def por_defecto(cls):
        costos = [
            [1, 1, 1, 2, 2, 1, 1, 2, 3, 3, 2, 2],
            [1, 1, 2, 2, 2, 1, 2, 2, 3, 4, 3, 2],
            [2, 1, 1, 2, 3, 3, 2, 1, 2, 3, 4, 3],
            [2, 2, 2, 1, 1, 3, 2, 1, 2, 2, 3, 3],
            [3, 3, 2, 1, 3, 4, 3, 2, 2, 3, 4, 4],
            [4, 3, 2, 3, 3, 3, 4, 3, 2, 2, 3, 4],
            [3, 3, 2, 3, 1, 4, 3, 3, 2, 2, 3, 3],
            [2, 2, 2, 3, 3, 3, 1, 1, 3, 2, 2, 3],
            [2, 3, 3, 3, 4, 3, 3, 1, 2, 1, 2, 3],
            [2, 4, 3, 2, 3, 2, 2, 3, 2, 1, 2, 4],
            [3, 3, 2, 2, 2, 2, 3, 3, 2, 2, 1, 3],
            [3, 2, 2, 2, 3, 3, 3, 3, 2, 3, 2, 1],
        ]
        obstaculos = [[3, 3], [4, 3], [3, 4], [6, 6], [6, 7], [7, 7], [7, 8]]
        entregas = [
            {"id": "E1", "nombre": "Entrega 1", "x": 1, "y": 2, "demanda": 10,
             "recursos": {"combustible": 10, "permisos": 1, "tiempo": 8}},
            {"id": "E2", "nombre": "Entrega 2", "x": 2, "y": 8, "demanda": 14,
             "recursos": {"combustible": 14, "permisos": 2, "tiempo": 10}},
            {"id": "E3", "nombre": "Entrega 3", "x": 6, "y": 1, "demanda": 8,
             "recursos": {"combustible": 8, "permisos": 1, "tiempo": 6}},
            {"id": "E4", "nombre": "Entrega 4", "x": 9, "y": 4, "demanda": 12,
             "recursos": {"combustible": 12, "permisos": 2, "tiempo": 9}},
            {"id": "E5", "nombre": "Entrega 5", "x": 8, "y": 10, "demanda": 16,
             "recursos": {"combustible": 16, "permisos": 2, "tiempo": 12}},
        ]
        return cls(
            nombre="Escenario logístico 12x12",
            filas=12,
            columnas=12,
            inicio=(0, 0),
            destino=(11, 11),
            entregas=entregas,
            mapa=Mapa(filas=12, columnas=12, costos=costos,
                      obstaculos=obstaculos),
            recursos={"combustible": 120, "permisos": 12, "tiempo": 80},
            competidor={"nombre": "TransLog", "efecto_costo": 1.18,
                        "reduccion_recurso": 0.15, "agresividad": 0.6},
            semilla=42,
        )
