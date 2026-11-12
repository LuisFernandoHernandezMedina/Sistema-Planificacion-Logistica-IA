# -*- coding: utf-8 -*-
"""Verifica que las cifras citadas en README e INFORME coincidan con los CSV.

Uso:  python experimentos/verificar_consistencia.py
Falla (código 1) si alguna cifra documentada no está respaldada por los
resultados exportados en experimentos/resultados/. No compara tiempos.
"""
import csv
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(RAIZ, "experimentos", "resultados")


def leer(nombre):
    with open(os.path.join(RES, nombre), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def numero(x):
    return float(x)


def main():
    meta = {f["metodo"]: f for f in leer("resumen_metaheuristicas.csv")}
    mm = {f["metodo"]: f for f in leer("resultados_minimax.csv")}
    plan = leer("resultados_planificacion_final.csv")[0]
    sa, ga = meta["recocido_simulado"], meta["algoritmo_genetico"]

    esperadas = [
        ("mejor costo SA", "%.1f" % numero(sa["mejor_costo"])),
        ("promedio GA", "%.2f" % numero(ga["costo_promedio"])),
        ("desv. GA", "%.4f" % numero(ga["desviacion_estandar"])),
        ("peor GA", "%.1f" % numero(ga["peor_costo"])),
        ("nodos minimax", str(int(mm["sin_poda"]["nodos_visitados"]))),
        ("nodos alfa-beta", str(int(mm["alfa_beta"]["nodos_visitados"]))),
        ("podados", str(int(mm["alfa_beta"]["nodos_podados"]))),
        ("costo integrado", "%.4f" % numero(plan["costo_total_integrado"])),
    ]
    ok = True
    for archivo in ("README.md", "INFORME_TECNICO.md"):
        with open(os.path.join(RAIZ, archivo), encoding="utf-8") as f:
            texto = f.read()
        for nombre, valor in esperadas:
            if valor not in texto:
                print("[FALTA] %s: %s=%s no aparece en el documento"
                      % (archivo, nombre, valor))
                ok = False
        # Cifras antiguas que no deben reaparecer
        for viejo in (r"\b74\.0\b", r"\b116\.05"):
            if re.search(viejo, texto):
                print("[OBSOLETO] %s contiene %s" % (archivo, viejo))
                ok = False
    if abs(numero(mm["sin_poda"]["valor_minimax"])
           - numero(mm["alfa_beta"]["valor_minimax"])) > 1e-9:
        print("[ERROR] valor minimax distinto con y sin poda")
        ok = False
    if (int(mm["alfa_beta"]["nodos_visitados"]) + int(mm["alfa_beta"]["nodos_podados"])
            != int(mm["sin_poda"]["nodos_visitados"])):
        print("[ERROR] visitados + podados != nodos de minimax")
        ok = False
    print("Consistencia README/INFORME vs CSV:", "OK" if ok else "CON ERRORES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
