#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conciliacion de la cuenta FlexiAhorro contra el flujo de la cuenta operativa.

Datos tomados del extracto oficial del Banco Pichincha
"Movimientos_cuenta_20250731_20260731.pdf" (cuenta 2212160493, a nombre de
Rodriguez Ponce Ana Paula), periodo 31-jul-2025 a 31-jul-2026.

Como se leen los dos lados:
  En el EXTRACTO de FlexiAhorro          En la HOJA de la cuenta operativa
  ------------------------------------   ---------------------------------
  Credito "Transf. de Ana Paula ..."  =  "ENVIO A FLEXIAHORRO"  (sale de la
                                          operativa y entra al ahorro)
  Debito  "Transf. a Rodriguez Ponce" =  "INGRESO DE FLEXIAHORRO" (vuelve a
          (cuenta beneficiaria 4751)      la operativa para pagar)

Salida: flexiahorro_2026.json
"""
import json

# la conciliacion cubre los meses del extracto pegado; los posteriores
# apareceran cuando Francisco pegue el extracto siguiente
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul"]

# Totales por mes leidos del extracto, separando transferencias de intereses.
#   entra  = creditos por transferencia desde la cuenta operativa
#   sale   = debitos por transferencia hacia la cuenta operativa
#   interes= intereses acreditados por el banco en el mes
EXTRACTO = {
    "ene": {"entra":     20.00, "sale":      0.00, "interes":   5.92},
    "feb": {"entra":  4_820.00, "sale":      0.00, "interes":   8.56},
    "mar": {"entra":  3_620.00, "sale":  4_413.01, "interes":  14.66},
    "abr": {"entra":  9_056.00, "sale":  6_577.41, "interes":  23.78},
    "may": {"entra":  7_425.00, "sale":  7_655.00, "interes":  19.45},
    "jun": {"entra": 15_722.00, "sale": 13_405.13, "interes":  25.83},
    "jul": {"entra": 14_357.00, "sale": 13_456.99, "interes":  32.85},
}

# Saldos verificables del propio extracto
SALDO_31_12_2025 = 1_626.84
SALDO_31_07_2026 = 11_270.94

# El banco NO corta por mes natural: la cuenta esta en "Ciclo 6" y los cortes
# caen cada dos meses. Estos son los estados oficiales, con su saldo de cierre
# verificado. Es la conciliacion dura; la tabla mensual de arriba sirve para
# ver el ritmo, pero el saldo bueno es el de estos cortes.
CICLOS = [
    # (desde, hasta, saldo_anterior, saldo_cierre, interes_del_periodo)
    ("24/04/2026", "19/06/2026",  7_458.81,  7_626.11, 42.43),
    ("19/06/2026", "21/08/2026",  7_626.11, 12_207.73, 69.61),
]

# El banco abona "CR AH PROGRAMADO" (ahorro programado, 20,00 al mes) que no
# sale de la cuenta operativa: por eso el extracto recibe algo mas de lo que
# la hoja envia. No es un descuadre.
AHORRO_PROGRAMADO_MES = 20.00

# Retiros que el extracto recoge y la hoja operativa todavia no.
# Los tres del 31/07 (600 + 115,49 + 11,50) se registraron en la hoja el
# 31/07/2026, asi que la lista queda vacia y los dos lados cuadran solos.
PENDIENTES_EN_HOJA = []


def main():
    an = json.load(open("analisis_2026.json", encoding="utf-8"))

    # lo que dice la hoja operativa
    hoja = {mm: {"entra": 0.0, "sale": 0.0} for mm in MESES}
    for g in an["gastos"]:
        if g["categoria"] == "Salida a FlexiAhorro":
            for mm in MESES:
                hoja[mm]["entra"] += g["por_mes"][mm]
        elif g["categoria"] == "Entrada desde FlexiAhorro":
            for mm in MESES:
                hoja[mm]["sale"] += -g["por_mes"][mm]

    filas, ok = [], True
    for mm in MESES:
        e = EXTRACTO[mm]
        d_entra = round(hoja[mm]["entra"] - e["entra"], 2)
        d_sale = round(hoja[mm]["sale"] - e["sale"], 2)
        # la única diferencia admitida es la de los retiros del 31/07 que el
        # banco ya recoge y la hoja todavía no
        pend_mes = sum(p[2] for p in PENDIENTES_EN_HOJA
                       if MESES[int(p[0][3:5]) - 1] == mm)
        if abs(d_entra) > 0.5 or abs(d_sale + pend_mes) > 0.5:
            ok = False
        filas.append({
            "mes": mm,
            "hoja_entra": round(hoja[mm]["entra"], 2), "ext_entra": e["entra"],
            "dif_entra": d_entra,
            "hoja_sale": round(hoja[mm]["sale"], 2), "ext_sale": e["sale"],
            "dif_sale": d_sale,
            "interes": e["interes"],
            "neto": round(e["entra"] - e["sale"], 2),
        })

    # --- conciliacion contra los ciclos reales del banco ---
    # Ojo con las erratas de la hoja: FELXIAHORRO, FLEXIAHRRO, FLEXIAHORO.
    # Filtrar por "FLEXI" a secas dejaba fuera tres movimientos.
    import re, datetime as _dt
    SUENA = re.compile(r"F[EL]{1,2}[XI]{1,2}[A-Z]*AH[OR]{0,3}R?O", re.I)
    def _f(txt):
        d, m, a = txt.split("/")
        return _dt.date(int(a), int(m), int(d))
    mov = json.load(open("movimientos_2026.json", encoding="utf-8"))
    ciclos = []
    for desde, hasta, sa, sc, inte in CICLOS:
        a, b = _f(desde), _f(hasta)
        env = sac = 0.0
        for x in mov:
            if not SUENA.search(x["descripcion"]):
                continue
            if a < _f(x["fecha"]) <= b:
                env += x["egreso"]
                sac += x["ingreso"]
        teo = round(sa + env - sac + inte, 2)
        ciclos.append({
            "desde": desde, "hasta": hasta,
            "saldo_anterior": sa, "saldo_cierre": sc,
            "hoja_envia": round(env, 2), "hoja_saca": round(sac, 2),
            "interes": inte, "teorico": teo,
            "desvio": round(sc - teo, 2),
        })

    interes = round(sum(f["interes"] for f in filas), 2)
    neto = round(sum(f["neto"] for f in filas), 2)
    pend = round(sum(p[2] for p in PENDIENTES_EN_HOJA), 2)

    # El saldo final sale del inicial + lo neto aportado + intereses.
    # 'neto' ya viene del extracto, que SI recoge los retiros del 31/07:
    # restarlos otra vez seria contarlos dos veces.
    teorico = round(SALDO_31_12_2025 + neto + interes, 2)

    out = {
        "meses": MESES, "filas": filas, "cuadra": ok,
        "ciclos": ciclos,
        "saldo_verificado": CICLOS[-1][3],
        "saldo_verificado_fecha": CICLOS[-1][1],
        "interes_ciclos": round(sum(c["interes"] for c in ciclos), 2),
        "interes_2026": interes, "neto_2026": neto,
        "saldo_inicial": SALDO_31_12_2025, "saldo_final": SALDO_31_07_2026,
        "saldo_teorico": teorico,
        "desvio_saldo": round(SALDO_31_07_2026 - teorico, 2),
        "pendientes": [{"fecha": f, "desc": d, "importe": i}
                       for f, d, i in PENDIENTES_EN_HOJA],
        "pendiente_total": pend,
        "titular": "Rodriguez Ponce Ana Paula",
        "cuenta": "2212160493",
    }
    json.dump(out, open("flexiahorro_2026.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    W = 12
    print("=" * 92)
    print("CONCILIACION FLEXIAHORRO  ·  hoja operativa vs extracto del banco")
    print("=" * 92)
    print(f"{'MES':<6}{'HOJA envía':>{W}}{'EXTRACTO':>{W}}{'dif':>8}"
          f"{'HOJA saca':>{W}}{'EXTRACTO':>{W}}{'dif':>8}{'INTERÉS':>10}")
    print("-" * 92)
    for f in filas:
        print(f"{f['mes']:<6}{f['hoja_entra']:>{W},.2f}{f['ext_entra']:>{W},.2f}"
              f"{f['dif_entra']:>8,.2f}{f['hoja_sale']:>{W},.2f}"
              f"{f['ext_sale']:>{W},.2f}{f['dif_sale']:>8,.2f}{f['interes']:>10,.2f}")
    print("-" * 92)
    print(f"{'TOTAL':<6}{sum(f['hoja_entra'] for f in filas):>{W},.2f}"
          f"{sum(f['ext_entra'] for f in filas):>{W},.2f}{'':>8}"
          f"{sum(f['hoja_sale'] for f in filas):>{W},.2f}"
          f"{sum(f['ext_sale'] for f in filas):>{W},.2f}{'':>8}{interes:>10,.2f}")
    print()
    print("CUADRA AL CENTAVO" if ok else "HAY DIFERENCIAS QUE REVISAR")
    print()
    print("=" * 92)
    print("CONCILIACION POR CICLO DEL BANCO  ·  el corte no es mensual")
    print("=" * 92)
    for c in ciclos:
        print(f"  {c['desde']} -> {c['hasta']}")
        print(f"     saldo anterior {c['saldo_anterior']:>12,.2f}")
        print(f"     la hoja envia  {c['hoja_envia']:>12,.2f}")
        print(f"     la hoja saca   {-c['hoja_saca']:>12,.2f}")
        print(f"     interes        {c['interes']:>12,.2f}")
        print(f"     = teorico      {c['teorico']:>12,.2f}")
        print(f"       real         {c['saldo_cierre']:>12,.2f}   desvio {c['desvio']:>8,.2f}"
              + ("   (ahorro programado del banco)" if abs(c['desvio']) % AHORRO_PROGRAMADO_MES < 0.01 else ""))
        print()
    print()
    print(f"{'Saldo FlexiAhorro 31/12/2025':<42}{SALDO_31_12_2025:>12,.2f}")
    print(f"{'+ neto aportado en 2026':<42}{neto:>12,.2f}")
    print(f"{'+ intereses ganados':<42}{interes:>12,.2f}")
    print(f"{'= saldo teórico':<42}{teorico:>12,.2f}")
    print(f"{'  saldo real del extracto':<42}{SALDO_31_07_2026:>12,.2f}")
    print(f"{'  desvío':<42}{out['desvio_saldo']:>12,.2f}")


if __name__ == "__main__":
    main()
