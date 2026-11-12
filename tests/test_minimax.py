# -*- coding: utf-8 -*-
"""Pruebas del módulo E: Minimax y poda alfa-beta."""

from algoritmos.minimax import (
    comparar_minimax_alfa_beta,
    minimax,
    minimax_alfa_beta,
)


def test_valores_iguales_profundidad_completa(escenario):
    resultado = comparar_minimax_alfa_beta(escenario)
    assert resultado["valores_iguales"]
    assert resultado["sin_poda"]["valor_minimax"] == \
        resultado["con_poda"]["valor_minimax"]
    assert resultado["sin_poda"]["profundidad_completa"]
    assert resultado["sin_poda"]["nodos_visitados"] > 0


def test_poda_reduce_nodos(escenario):
    resultado = comparar_minimax_alfa_beta(escenario)
    assert resultado["con_poda"]["nodos_visitados"] <= \
        resultado["sin_poda"]["nodos_visitados"]
    assert resultado["con_poda"]["nodos_podados"] > 0
    assert resultado["nodos_ahorrados"] > 0


def test_profundidad_limitada(escenario):
    resultado = comparar_minimax_alfa_beta(escenario, 2)
    assert resultado["valores_iguales"]
    assert resultado["sin_poda"]["profundidad_utilizada"] == 2
    assert not resultado["sin_poda"]["profundidad_completa"]
    assert resultado["sin_poda"]["evaluacion"].startswith("evaluación")


def test_reproducible(escenario):
    a = minimax(escenario)
    b = minimax(escenario)
    assert a["valor_minimax"] == b["valor_minimax"]
    assert a["nodos_visitados"] == b["nodos_visitados"]
    c = minimax_alfa_beta(escenario)
    d = minimax_alfa_beta(escenario)
    assert c["valor_minimax"] == d["valor_minimax"]
    assert c["nodos_visitados"] == d["nodos_visitados"]


def test_decision_es_una_entrega(escenario):
    resultado = minimax(escenario)
    nombres = [e.nombre for e in escenario.entregas]
    assert resultado["mejor_decision"] in nombres
    assert set(resultado["linea_principal"]).issubset(set(nombres))


def test_conteo_exacto_visitados_mas_podados(escenario):
    """alfa-beta: visitados + podados == nodos de minimax (cada profundidad)."""
    from algoritmos.minimax import comparar_minimax_alfa_beta
    n = len(escenario.entregas)
    for profundidad in range(1, n + 1):
        c = comparar_minimax_alfa_beta(escenario, profundidad)
        assert c["valores_iguales"]
        assert c["conteo_consistente"]
        assert (c["con_poda"]["nodos_visitados"] + c["con_poda"]["nodos_podados"]
                == c["sin_poda"]["nodos_visitados"])


def test_minimax_valor_conocido_en_juego_pequeno():
    """Valores (9, 5, 1): MAX toma 9 y 1, MIN toma 5 -> utilidad 5."""
    from types import SimpleNamespace
    from algoritmos.minimax import minimax, minimax_alfa_beta
    entregas = [SimpleNamespace(id=i, nombre="E%d" % i, demanda=d - 5)
                for i, d in enumerate((9, 5, 1))]
    esc = SimpleNamespace(entregas=entregas)
    assert minimax(esc)["valor_minimax"] == 5.0
    assert minimax_alfa_beta(esc)["valor_minimax"] == 5.0


def test_evaluacion_aproximada_con_profundidad_limitada(escenario):
    from algoritmos.minimax import minimax_alfa_beta
    r = minimax_alfa_beta(escenario, 2)
    assert not r["profundidad_completa"]
    assert "aproximada" in r["evaluacion"]
