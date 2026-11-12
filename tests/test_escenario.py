# -*- coding: utf-8 -*-
"""Pruebas del escenario, la cuadrícula y las validaciones."""

import copy

import pytest

from core.escenario import Escenario
from core.mapa import Mapa


def test_escenario_por_defecto_valido(escenario):
    assert escenario.filas == 12
    assert escenario.columnas == 12
    assert len(escenario.entregas) >= 3
    assert escenario.validar() == []
    assert escenario.esta_conectado()


def test_punto_fuera_de_cuadricula():
    escenario = Escenario.por_defecto()
    escenario.entregas[0].x = 99
    errores = escenario.validar()
    assert any("fuera de la cuadrícula" in e for e in errores)


def test_punto_sobre_obstaculo():
    escenario = Escenario.por_defecto()
    entrega = escenario.entregas[0]
    escenario.mapa.obstaculos.add((entrega.x, entrega.y))
    errores = escenario.validar()
    assert any("obstáculo" in e for e in errores)


def test_puntos_duplicados():
    escenario = Escenario.por_defecto()
    escenario.entregas[1].x = escenario.entregas[0].x
    escenario.entregas[1].y = escenario.entregas[0].y
    errores = escenario.validar()
    assert any("comparte celda" in e for e in errores)


def test_nombres_duplicados():
    escenario = Escenario.por_defecto()
    escenario.entregas[1].nombre = escenario.entregas[0].nombre
    errores = escenario.validar()
    assert any("repetido" in e for e in errores)


def test_inicio_sobre_obstaculo():
    escenario = Escenario.por_defecto()
    escenario.mapa.obstaculos.add(escenario.inicio)
    errores = escenario.validar()
    assert any("inicio está sobre un obstáculo" in e for e in errores)


def test_recursos_insuficientes():
    escenario = Escenario.por_defecto()
    escenario.recursos["combustible"] = 1
    errores = escenario.validar()
    assert any("Recursos insuficientes" in e for e in errores)


def test_menos_de_tres_entregas():
    escenario = Escenario.por_defecto()
    escenario.entregas = escenario.entregas[:2]
    errores = escenario.validar()
    assert any("al menos tres" in e for e in errores)


def test_mapa_costos_invalidos():
    with pytest.raises(ValueError):
        Mapa(filas=2, columnas=2, costos=[[1, 0], [1, 1]])
    with pytest.raises(ValueError):
        Mapa(filas=2, columnas=2, costos=[[1, 1]])


def test_json_roundtrip(escenario):
    datos = copy.deepcopy(escenario.to_dict())
    recuperado = Escenario.desde_dict(datos)
    assert recuperado.inicio == escenario.inicio
    assert recuperado.destino == escenario.destino
    assert len(recuperado.entregas) == len(escenario.entregas)
    assert recuperado.mapa.obstaculos == escenario.mapa.obstaculos
    assert recuperado.validar() == []


def test_csv_roundtrip(escenario):
    texto = escenario.to_csv_text()
    recuperado = Escenario.desde_csv_texto(texto)
    assert recuperado.filas == escenario.filas
    assert recuperado.columnas == escenario.columnas
    assert recuperado.inicio == escenario.inicio
    assert recuperado.destino == escenario.destino
    assert recuperado.mapa.obstaculos == escenario.mapa.obstaculos
    assert [e.nombre for e in recuperado.entregas] == \
        [e.nombre for e in escenario.entregas]
    assert recuperado.recursos.keys() == escenario.recursos.keys()
    for clave in escenario.recursos:
        assert recuperado.recursos[clave] == pytest.approx(
            escenario.recursos[clave])
    assert recuperado.competidor["nombre"] == escenario.competidor["nombre"]
    assert recuperado.validar() == []
