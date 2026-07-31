#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria de cobertura: que movimiento de la hoja aparece en que tabla del
panel, y sobre todo cuales NO salen en ninguna.

Cada movimiento deberia poder encontrarse en al menos una tabla. Si alguno
no aparece, o esta mal clasificado o falta una tabla que lo recoja.
"""
import json
from collections import defaultdict

TABLAS = {
    "t-pl":       "02 · P&L mes a mes",
    "t-hon":      "05 · Tarifario por cuenta",
    "t-cli-mes":  "06 · Cobros por cuenta",
    "t-eq":       "07 · Nómina",
    "t-gastos":   "08 · Todo lo demás",
    "t-tarjeta":  "09 · Tarjeta",
    "t-flexi":    "10 · Conciliación FlexiAhorro",
}

# Grupos tal y como los reparte cada tabla del panel
G_NOMINA = {"Nomina fija", "Nomina socios", "Nomina variable", "Pasantias"}
G_CLIENTE = {"Ingresos - Fee mensual", "Ingresos - Produccion"}
G_INGRESO = G_CLIENTE | {"Ingresos - Pauta", "Otros ingresos",
                         "Ingresos - Sin identificar"}
G_TRANSFER = {"Movimiento entre cuentas propias"}


def donde(m):
    """Tablas del panel en las que se puede ver este movimiento."""
    g, t = m["grupo"], []
    if g in G_NOMINA:
        t += ["t-eq", "t-pl"]
    elif g in G_CLIENTE:
        t += ["t-cli-mes", "t-hon", "t-pl"]
    elif g == "Ingresos - Pauta":
        # la pauta que devuelve un cliente sale en su fila mensual
        t += ["t-cli-mes", "t-pl"]
    elif g == "Ingresos - Sin identificar":
        t += ["t-cli-mes", "t-pl"]
    elif g == "Otros ingresos":
        # desde ahora tienen su propio bloque en la tabla de cobros
        t += ["t-cli-mes", "t-pl"]
    elif g in G_TRANSFER:
        t += ["t-gastos", "t-flexi"]
    elif g == "Saldo Inicial":
        t += []                    # no es un movimiento del ejercicio
    elif g == "Retiro de socios":
        t += ["t-gastos"]
    else:
        t += ["t-gastos", "t-pl"]
    if g == "Tarjeta de credito":
        t += ["t-tarjeta"]
    return t


def main():
    mov = json.load(open("movimientos_2026.json", encoding="utf-8"))

    cobertura = defaultdict(lambda: {"n": 0, "monto": 0.0})
    huerfanos, solo_pl = [], []
    for m in mov:
        t = donde(m)
        imp = m["ingreso"] - m["egreso"]
        for x in t:
            cobertura[x]["n"] += 1
            cobertura[x]["monto"] += abs(imp)
        if not t:
            huerfanos.append(m)
        elif t == ["t-pl"]:
            solo_pl.append(m)

    print("=" * 84)
    print("COBERTURA: cuántos movimientos se pueden ver en cada tabla")
    print("=" * 84)
    for k, lab in TABLAS.items():
        c = cobertura[k]
        print(f"  {lab:<34}{c['n']:>5} movs{c['monto']:>14,.2f}")

    print(f"\nTotal de movimientos en la hoja: {len(mov)}")

    print("\n" + "=" * 84)
    print("SIN TABLA PROPIA: sólo entran en el total del P&L")
    print("=" * 84)
    if solo_pl:
        por_cat = defaultdict(lambda: {"n": 0, "monto": 0.0, "ej": []})
        for m in solo_pl:
            k = (m["grupo"], m["categoria"])
            por_cat[k]["n"] += 1
            por_cat[k]["monto"] += m["ingreso"] - m["egreso"]
            if len(por_cat[k]["ej"]) < 4:
                por_cat[k]["ej"].append(
                    f"{m['fecha']} {m['descripcion'][:44]} "
                    f"{m['ingreso'] - m['egreso']:+,.2f}")
        for (g, c), v in sorted(por_cat.items(), key=lambda x: -abs(x[1]["monto"])):
            print(f"\n  {g} / {c}   ->  {v['n']} movs, {v['monto']:+,.2f}")
            for e in v["ej"]:
                print(f"      {e}")
    else:
        print("  ninguno")

    print("\n" + "=" * 84)
    print("HUÉRFANOS: no aparecen en ninguna tabla")
    print("=" * 84)
    if huerfanos:
        for m in huerfanos:
            print(f"  {m['fecha']}  {m['ingreso'] - m['egreso']:>12,.2f}  "
                  f"{m['descripcion'][:46]:46} [{m['grupo']}]")
    else:
        print("  ninguno")

    # --------- todos los ingresos, vengan de donde vengan ---------
    print("\n" + "=" * 84)
    print("TODOS LOS INGRESOS DE LA AGENCIA")
    print("=" * 84)
    ing = defaultdict(lambda: {"n": 0, "monto": 0.0})
    for m in mov:
        if m["ingreso"] <= 0 or m["grupo"] in G_TRANSFER or m["grupo"] == "Saldo Inicial":
            continue
        ing[m["grupo"]]["n"] += 1
        ing[m["grupo"]]["monto"] += m["ingreso"]
    tot = sum(v["monto"] for v in ing.values())
    for g, v in sorted(ing.items(), key=lambda x: -x[1]["monto"]):
        print(f"  {g:<34}{v['monto']:>12,.2f}{v['n']:>5} movs"
              f"{v['monto']/tot*100:>7.1f}%")
    print(f"  {'TOTAL':<34}{tot:>12,.2f}")

    # ingresos que no vienen de una cuenta de cliente
    print("\n  De ahí, lo que NO es una cuenta de cliente:")
    for m in mov:
        if m["ingreso"] > 0 and m["grupo"] in ("Otros ingresos",
                                               "Ingresos - Sin identificar"):
            print(f"      {m['fecha']}  {m['ingreso']:>9,.2f}  "
                  f"{m['descripcion'][:48]:48} [{m['categoria']}]")


if __name__ == "__main__":
    main()
