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
_corte = datos.get("mes_corte_activo", "jul")
_orden12 = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
cli_act = [c for c in datos["clientes"]
           if c["ultimo_mes"] and _orden12.index(c["ultimo_mes"]) >= _orden12.index(_corte)]
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
    # Desglose de los reembolsos de pauta a Francisco. Un concepto por fila
    # con su importe en cada mes, para poder comparar de un golpe: el libro
    # solo ve un movimiento mensual, esto dice de que se compone.
    #   `recupera` marca lo que el cliente devuelve, asi se ve el costo real.
    #   Nombres unificados: en la tabla de cada mes algunos vienen escritos
    #   distinto (CapCut / CapCut agencia, Tap Bios / Varios Tap Bios).
    #   El flag de agosto se infiere de la clasificacion de septiembre: los
    #   conceptos se repiten mes a mes y la tabla de agosto no la traia.
    "pauta_items": [
        {"concepto": "Pauta Pladeco Alpes",      "tipo": "Pauta",    "recupera": True,  "por_mes": {"ago": 384.00, "sep": 384.00}},
        {"concepto": "Freepik/Magnific cta 1",   "tipo": "Software", "recupera": False, "por_mes": {"ago": 376.36}},
        {"concepto": "Campaña Healthy",          "tipo": "Pauta",    "recupera": True,  "por_mes": {"ago": 300.00, "sep": 300.00}},
        {"concepto": "Pauta Pladeco Santa Rosa", "tipo": "Pauta",    "recupera": True,  "por_mes": {"ago": 256.00, "sep": 256.00}},
        {"concepto": "CapCut",                   "tipo": "Software", "recupera": False, "por_mes": {"ago": 68.88,  "sep": 68.88}},
        {"concepto": "ManyChat Samari",          "tipo": "Software", "recupera": True,  "por_mes": {"ago": 52.60,  "sep": 52.50}},
        {"concepto": "Chatfuel MMWings",         "tipo": "Software", "recupera": True,  "por_mes": {"ago": 31.50,  "sep": 31.50}},
        {"concepto": "Freepik cta 2",            "tipo": "Software", "recupera": False, "por_mes": {"ago": 31.00,  "sep": 31.00}},
        {"concepto": "Adobe agencia cta 1",      "tipo": "Software", "recupera": False, "por_mes": {"ago": 30.51,  "sep": 30.51}},
        {"concepto": "Adobe agencia cta 2",      "tipo": "Software", "recupera": False, "por_mes": {"ago": 29.98,  "sep": 29.98}},
        {"concepto": "Tap Bios",                 "tipo": "Software", "recupera": False, "por_mes": {"ago": 25.20,  "sep": 25.20}},
        {"concepto": "Make",                     "tipo": "Software", "recupera": False, "por_mes": {"ago": 24.68,  "sep": 24.68}},
        {"concepto": "Google espacio agencia",   "tipo": "Software", "recupera": False, "por_mes": {"ago": 24.00,  "sep": 24.00}},
        {"concepto": "Personajes Healthy",       "tipo": "Pauta",    "recupera": True,  "por_mes": {"sep": 24.00}},
        {"concepto": "Chatfuel Healthy",         "tipo": "Software", "recupera": False, "por_mes": {"ago": 18.90,  "sep": 18.90}},
        {"concepto": "ManyChat Velas",           "tipo": "Software", "recupera": False, "por_mes": {"ago": 18.00,  "sep": 18.00}},
        {"concepto": "Reproducciones Healthy",   "tipo": "Pauta",    "recupera": True,  "por_mes": {"ago": 18.00,  "sep": 18.00}},
        {"concepto": "ElevenLabs Samari",        "tipo": "Software", "recupera": False, "por_mes": {"ago": 7.97,   "sep": 7.97}},
    ],
}

html = open("dashboard_template.html", encoding="utf-8").read()
html = html.replace("/*__DATOS__*/null",
                    json.dumps(datos, ensure_ascii=False))
open("panel-financiero-2026.html", "w", encoding="utf-8").write(html)
print("panel-financiero-2026.html generado ->", len(html), "bytes")
