#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inyecta analisis_2026.json dentro de la plantilla del panel."""
import json, io

datos = json.load(open("analisis_2026.json", encoding="utf-8"))
mov = json.load(open("movimientos_2026.json", encoding="utf-8"))

# --------- metricas derivadas que usa el simulador -------------------------
eq = datos["equipo"]
fijos_act = [e for e in eq if e["grupo"] == "Nomina fija" and e["activo_julio"]]
costo_persona = sum(e["promedio_mes"] for e in fijos_act) / len(fijos_act)
cli_act = [c for c in datos["clientes"] if c["ultimo_mes"] == "jul"]
fee_medio = sum(c["fee_promedio"] for c in cli_act) / len(cli_act)

tarif = json.load(open("tarifario_2026.json", encoding="utf-8"))
datos["tarifario"] = tarif
for clave, fichero in [("flexi", "flexiahorro_2026.json"),
                       ("tarjeta", "tarjeta_2026.json")]:
    try:
        datos[clave] = json.load(open(fichero, encoding="utf-8"))
    except FileNotFoundError:
        datos[clave] = None

# saldos leidos de los propios movimientos, nunca fijados a mano:
# la hoja crece cada semana y un numero quemado se queda obsoleto.
saldo_ini = next((m["ingreso"] for m in mov if m["grupo"] == "Saldo Inicial"), 0.0)
saldo_fin = round(sum(m["ingreso"] for m in mov) - sum(m["egreso"] for m in mov), 2)
ultima = mov[-1]["fecha"]

g = datos["grupos"]
datos["extra"] = {
    "costo_persona": round(costo_persona, 2),
    "fee_medio": round(fee_medio, 2),
    "clientes_activos": len(cli_act),
    "plantilla_fija": len(fijos_act),
    "pauta_pagada": round(-sum(g["Pauta"].values()), 2),
    "pauta_recuperada": round(tarif["totales"]["pauta"], 2),
    "pauta_no_recuperada": round(sum(p["pauta_neta"] for p in datos["pl"]), 2),
    "honorarios_mes": tarif["honorarios_recurrentes_mes"],
    "retenido_mes": tarif["retenido_mes"],
    "tarjeta_sin_desglose": round(-sum(g["Tarjeta de credito"].values()), 2),
    "a_cuentas_propias": round(
        -sum(datos["no_operativo"]["Movimiento entre cuentas propias"].values()), 2),
    "saldo_inicial": round(saldo_ini, 2),
    "saldo_final": saldo_fin,
    "ultima_fecha": ultima,
    "n_movimientos": len(mov),
}

html = open("dashboard_template.html", encoding="utf-8").read()
html = html.replace("/*__DATOS__*/null",
                    json.dumps(datos, ensure_ascii=False))
open("panel-financiero-2026.html", "w", encoding="utf-8").write(html)
print("panel-financiero-2026.html generado ->", len(html), "bytes")
