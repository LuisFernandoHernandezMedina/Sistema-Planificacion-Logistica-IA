# -*- coding: utf-8 -*-
"""Configuración común de las pruebas."""

import os
import sys

import pytest

RUTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RUTA_RAIZ not in sys.path:
    sys.path.insert(0, RUTA_RAIZ)

from core.escenario import Escenario  # noqa: E402
from core.mapa import Mapa  # noqa: E402
from core.costos import construir_matriz_costos  # noqa: E402


@pytest.fixture
def escenario():
    return Escenario.por_defecto()


@pytest.fixture
def datos_costos(escenario):
    return construir_matriz_costos(escenario)


@pytest.fixture
def mapa_sin_solucion():
    costos = [[1.0 for _ in range(5)] for _ in range(5)]
    obstaculos = [[2, y] for y in range(5)]
    return Mapa(filas=5, columnas=5, costos=costos, obstaculos=obstaculos)
