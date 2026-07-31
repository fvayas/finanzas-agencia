#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desglose de la tarjeta de credito Mastercard 5213-xxxx-xxxx-3129.

Hasta ahora la hoja solo registraba "PAGO TARJETA DE CREDITO" sin decir en
que se gastaba: 1.472 dolares ciegos. Aqui van los consumos uno a uno,
tomados de los siete estados de cuenta del Banco Pichincha (ene-jul 2026).

Ojo con los periodos: cada estado va del 7 del mes anterior al 6 del mes de
emision, asi que un consumo de diciembre aparece en el estado de enero.
El mes que se usa aqui es el del ESTADO, para poder cruzarlo con los pagos
que hace la hoja.

Salida: tarjeta_2026.json
"""
import json
from collections import defaultdict

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul"]

# Que es cada comercio. La tarjeta se usa para tres cosas:
#   PAUTA     -> anuncios de TikTok
#   SOFTWARE  -> suscripciones de herramientas
#   OFICINA   -> comida y suministros sueltos
#   IMPUESTOS -> retencion de IVA sobre servicios digitales
#   FINANCIERO-> intereses por no pagar el total
COMERCIOS = {
    "TIKTOK":        ("Pauta",     "TikTok Ads"),
    "OPENAI":        ("Software",  "ChatGPT"),
    "WHATAFORM":     ("Software",  "Whataform"),
    "OPUS CLIP":     ("Software",  "Opus Clip"),
    "CAPCUT":        ("Software",  "CapCut"),
    "APPLE.COM":     ("Software",  "Apple"),
    "SPEEDY COM":    ("Software",  "Speedy Com"),
    "TOGO":          ("Oficina",   "Comida y cafetería"),
    "TO GO":         ("Oficina",   "Comida y cafetería"),
    "SWEET COFFEE":  ("Oficina",   "Comida y cafetería"),
    "SUPERMERCADOS": ("Oficina",   "Comida y cafetería"),
}

# (mes del estado, fecha del consumo, descripcion tal cual, importe)
CONSUMOS = [
    # --- estado de ENERO (07/12/2025 - 06/01/2026) ---
    ("ene", "10/12", "WHATAFORM CA USA",            79.80),
    ("ene", "18/12", "OPUS CLIP 218ECU",            23.00),
    ("ene", "28/12", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("ene", "30/12", "PTP - DL - TIKTOK",          100.00),
    # --- FEBRERO (07/01 - 06/02) ---
    ("feb", "10/01", "WHATAFORM CA USA",            79.80),
    ("feb", "18/01", "OPUS CLIP ECUECU",            23.00),
    ("feb", "28/01", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("feb", "04/02", "TOGO EXPRESS MART",            2.25),
    ("feb", "05/02", "CAPCUT ECUECU",                2.79),
    # --- MARZO (07/02 - 06/03) ---
    ("mar", "10/02", "WHATAFORM ECUECU",            79.80),
    ("mar", "18/02", "OPUS CLIP ECUECU",            23.00),
    ("mar", "23/02", "TO GO ECUECU",                 3.25),
    ("mar", "28/02", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("mar", "05/03", "CAPCUT ECU",                  13.99),
    # --- ABRIL (07/03 - 06/04) ---
    ("abr", "10/03", "WHATAFORM ECUECU",            79.80),
    ("abr", "15/03", "DLOCAL TIKTOK",              100.00),
    ("abr", "18/03", "OPUS CLIP ECUECU",            23.00),
    ("abr", "18/03", "DLOCAL TIKTOK",              100.00),
    ("abr", "28/03", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("abr", "02/04", "DLOCAL TIKTOK",              100.00),
    ("abr", "05/04", "CAPCUT ECUECU",               13.99),
    # --- MAYO (07/04 - 06/05) ---
    ("may", "10/04", "WHATAFORM ECUECU",            28.37),
    ("may", "18/04", "SWEET COFFEE",                 3.90),
    ("may", "18/04", "OPUS CLIP ECUECU",            23.00),
    ("may", "28/04", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("may", "28/04", "APPLE.COM/BILLSA",            14.28),
    ("may", "29/04", "APPLE.COM/BILLSA",             0.69),
    ("may", "05/05", "CAPCUT 002ARG",               13.99),
    # --- JUNIO (07/05 - 06/06) ---
    ("jun", "10/05", "WHATAFORM BOGCOL",            53.20),
    ("jun", "18/05", "OPUS CLIP CA USA",            23.00),
    ("jun", "28/05", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("jun", "28/05", "APPLE.COM/BILLSA",             6.99),
    ("jun", "01/06", "SPEEDY COM P/R",              19.50),
    # --- JULIO (07/06 - 06/07) ---
    ("jul", "10/06", "WHATAFORM ECUECU",            53.20),
    ("jul", "18/06", "OPUS CLIP ECUECU",            23.00),
    ("jul", "28/06", "OPENAI *CHATGPT SUBSCR",      20.00),
    ("jul", "28/06", "APPLE.COM/BILLSA",             6.99),
    ("jul", "30/06", "SUPERMERCADOS LA CASERA",     10.19),
    ("jul", "01/07", "SPEEDY COM P/R",              19.50),
]

# Retencion de IVA sobre servicios digitales e intereses de financiamiento,
# tal y como los resume cada estado de cuenta.
CARGOS = {
    "ene": {"ret_iva": 14.97, "interes": 1.97},
    "feb": {"ret_iva": 15.39, "interes": 1.63},
    "mar": {"ret_iva": 20.52, "interes": 3.22},
    "abr": {"ret_iva": 20.52, "interes": 0.56},
    "may": {"ret_iva": 15.05, "interes": 3.01},
    "jun": {"ret_iva": 15.48, "interes": 3.65},
    "jul": {"ret_iva": 15.48, "interes": 0.77},
}

# Total a pagar que declara cada estado, para poder validar
TOTAL_ESTADO = {"ene": 239.74, "feb": 359.71, "mar": 494.24, "abr": 457.87,
                "may": 543.49, "jun": 141.82, "jul": 260.94}


def clasifica(desc):
    d = desc.upper()
    for clave, (fam, nombre) in COMERCIOS.items():
        if clave in d:
            return fam, nombre
    return "Sin identificar", desc.title()


def main():
    mov = json.load(open("movimientos_2026.json", encoding="utf-8"))

    # lo que la hoja registra como pagos de tarjeta
    pagos = defaultdict(float)
    detalle_pagos = defaultdict(list)
    for m in mov:
        if m["grupo"] == "Tarjeta de credito":
            pagos[m["mes"]] += m["egreso"] - m["ingreso"]
            detalle_pagos[m["mes"]].append(
                {"fecha": m["fecha"], "desc": m["descripcion"],
                 "importe": round(m["egreso"] - m["ingreso"], 2)})

    # consumos agrupados por concepto
    por_concepto = defaultdict(lambda: {"fam": "", "meses": defaultdict(float),
                                        "movs": []})
    for mes, fecha, desc, imp in CONSUMOS:
        fam, nombre = clasifica(desc)
        c = por_concepto[nombre]
        c["fam"] = fam
        c["meses"][mes] += imp
        c["movs"].append({"mes": mes, "fecha": fecha, "desc": desc,
                          "importe": imp})

    conceptos = []
    for nombre, c in sorted(por_concepto.items(),
                            key=lambda x: -sum(x[1]["meses"].values())):
        conceptos.append({
            "concepto": nombre, "familia": c["fam"],
            "total": round(sum(c["meses"].values()), 2),
            "n": len(c["movs"]),
            "por_mes": {mm: round(c["meses"][mm], 2) for mm in MESES},
            "movs": c["movs"],
        })

    # las dos lineas que no son compras sino cargos del banco
    for lab, k, fam in [("Retención IVA servicios digitales", "ret_iva", "Impuestos"),
                        ("Intereses por financiar el saldo", "interes", "Financiero")]:
        conceptos.append({
            "concepto": lab, "familia": fam,
            "total": round(sum(CARGOS[mm][k] for mm in MESES), 2),
            "n": len(MESES),
            "por_mes": {mm: CARGOS[mm][k] for mm in MESES},
            "movs": [{"mes": mm, "fecha": "", "desc": lab,
                      "importe": CARGOS[mm][k]} for mm in MESES],
        })

    tot_mes = {mm: round(sum(c["por_mes"][mm] for c in conceptos), 2)
               for mm in MESES}
    total = round(sum(tot_mes.values()), 2)
    pagado = round(sum(pagos.values()), 2)

    fam_tot = defaultdict(float)
    for c in conceptos:
        fam_tot[c["familia"]] += c["total"]

    out = {
        "meses": MESES, "conceptos": conceptos,
        "por_mes": tot_mes, "total": total,
        "familias": {k: round(v, 2) for k, v in
                     sorted(fam_tot.items(), key=lambda x: -x[1])},
        "pagado_hoja": pagado,
        "pagos_por_mes": {mm: round(pagos[mm], 2) for mm in MESES},
        "detalle_pagos": {mm: detalle_pagos[mm] for mm in MESES},
        "diferencia": round(pagado - total, 2),
        "tarjeta": "Mastercard ····3129",
        "titular": "Rodriguez Ponce Ana Paula",
    }
    json.dump(out, open("tarjeta_2026.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    W = 9
    print("=" * 96)
    print("EN QUÉ SE GASTA LA TARJETA")
    print("=" * 96)
    print(f"{'CONCEPTO':<30}{'FAMILIA':<13}" +
          "".join(f"{mm:>{W}}" for mm in MESES) + f"{'TOTAL':>10}")
    print("-" * 96)
    for c in conceptos:
        print(f"{c['concepto']:<30}{c['familia']:<13}" +
              "".join(f"{c['por_mes'][mm]:>{W},.2f}" if c["por_mes"][mm]
                      else f"{'—':>{W}}" for mm in MESES) +
              f"{c['total']:>10,.2f}")
    print("-" * 96)
    print(f"{'TOTAL CONSUMIDO':<43}" +
          "".join(f"{tot_mes[mm]:>{W},.2f}" for mm in MESES) + f"{total:>10,.2f}")
    print(f"{'PAGADO SEGÚN LA HOJA':<43}" +
          "".join(f"{out['pagos_por_mes'][mm]:>{W},.2f}" for mm in MESES) +
          f"{pagado:>10,.2f}")
    print()
    print("Reparto por familia:")
    for k, v in out["familias"].items():
        print(f"   {k:<14}{v:>9,.2f}   {v/total*100:>5.1f}%")
    print(f"\nConsumido {total:,.2f} · pagado {pagado:,.2f} · "
          f"diferencia {out['diferencia']:+,.2f}")
    print("La diferencia es saldo revolvente: no se paga el total cada mes.")


if __name__ == "__main__":
    main()
