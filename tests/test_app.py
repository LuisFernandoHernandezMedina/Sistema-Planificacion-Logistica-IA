# -*- coding: utf-8 -*-
"""Pruebas de los endpoints Flask."""

import pytest

from app import app
from core.escenario import Escenario


@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    with app.test_client() as cliente:
        respuesta = cliente.post("/api/escenario/restablecer")
        assert respuesta.status_code == 200
        yield cliente


def test_pagina_principal(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert b"Planificaci" in respuesta.data


def test_obtener_escenario(cliente):
    respuesta = cliente.get("/api/escenario")
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["validacion"]["valido"] is True
    assert datos["escenario"]["filas"] == 12
    assert datos["escenario"]["columnas"] == 12


def test_modulo_a_endpoint(cliente):
    respuesta = cliente.post("/api/busqueda_heuristica", json={})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["a_estrella"]["encontrado"] is True
    assert datos["greedy"]["encontrado"] is True


def test_modulo_b_endpoint(cliente):
    respuesta = cliente.post("/api/busqueda_local",
                             json={"soluciones_iniciales": 10, "max_iteraciones": 50})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["mejor"]["costo"] > 0
    assert len(datos["ejecuciones"]) == 10


def test_modulo_d_endpoint(cliente):
    respuesta = cliente.post("/api/teoria_juegos", json={})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert len(datos["matriz"]) == 3
    assert "equilibrios_nash" in datos


def test_modulo_e_endpoint(cliente):
    respuesta = cliente.post("/api/minimax", json={})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["valores_iguales"] is True


def test_escenario_invalido_rechazado(cliente):
    escenario = Escenario.por_defecto().to_dict()
    escenario["entregas"][0]["x"] = 99
    respuesta = cliente.post("/api/escenario", json={"escenario": escenario})
    assert respuesta.status_code == 400
    assert "detalles" in respuesta.get_json()


def test_escenario_sin_solucion(cliente):
    escenario = Escenario.por_defecto().to_dict()
    escenario["mapa"]["obstaculos"] = [[5, y] for y in range(12)]
    respuesta = cliente.post("/api/escenario", json={"escenario": escenario})
    assert respuesta.status_code == 200

    respuesta = cliente.post("/api/integracion", json={})
    assert respuesta.status_code == 400
    assert "ruta" in respuesta.get_json()["error"].lower()

    cliente.post("/api/escenario/restablecer")


def test_exportar_json_y_csv(cliente):
    respuesta = cliente.get("/api/escenario/exportar/json")
    assert respuesta.status_code == 200
    assert b"entregas" in respuesta.data

    respuesta = cliente.get("/api/escenario/exportar/csv")
    assert respuesta.status_code == 200
    assert b"recursos_globales" in respuesta.data


def test_integracion_endpoint(cliente):
    respuesta = cliente.post("/api/integracion", json={
        "parametros": {
            "recocido_simulado": {"iteraciones_por_temperatura": 5},
            "algoritmo_genetico": {"tamano_poblacion": 16, "generaciones": 10}
        }
    })
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert datos["planificacion_final"]["ruta_nombres"][0] == "Inicio"
    assert datos["modulo_e_minimax"]["valores_iguales"] is True
