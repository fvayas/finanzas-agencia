#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resumen ligero para la app de captura: qué falta por pagar este mes
(sueldos y gastos fijos aún sin registrar en la hoja) y qué falta por
cobrar a los clientes. Se publica como app-resumen.json junto al panel
y la app lo consulta al abrir.

La salida es determinística —sin marcas de hora— para que el robot de
cada 15 minutos no genere commits vacíos: el JSON solo cambia si cambian
los datos o al pasar de mes.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

BASE12 = ["ene", "feb", "mar", "abr", "may", "jun", "jul",
          "ago", "sep", "oct", "nov", "dic"]
NOMBRES = {"ene": "enero", "feb": "febrero", "mar": "marzo", "abr": "abril",
           "may": "mayo", "jun": "junio", "jul": "julio", "ago": "agosto",
           "sep": "septiembre", "oct": "octubre", "nov": "noviembre",
           "dic": "diciembre"}

# descripción sugerida al tocar un pendiente en la app (las que el
# categorizador del panel ya entiende a la primera)
SUGERENCIAS = {
    "Arriendo, condominio y alicuotas": "ARRIENDO OFICINA",
    "Internet": "INTERNET",
    "Limpieza": "PAGO LIMPIEZA",
    "Pago tarjeta (sin desglose)": "PAGO TARJETA DE CREDITO",
    "Impuestos": "PAGO IMPUESTOS",
    "Servicios basicos": "PAGO DE AGUA",
}

# movimientos entre cuentas propias o gasto variable: no son un "pago
# que falta", así que no entran al checklist
NO_CHECKLIST = {"Salida a FlexiAhorro", "Entrada desde FlexiAhorro",
                "Salida a Fideval", "Pauta pagada", "Devolucion a cliente",
                "Reverso bancario", "Utilidades"}


def main():
    an = json.load(open("analisis_2026.json", encoding="utf-8"))
    ta = json.load(open("tarifario_2026.json", encoding="utf-8"))

    mes = BASE12[datetime.now(ZoneInfo("America/Guayaquil")).month - 1]

    sueldos = []
    for e in an["equipo"]:
        if e["grupo"] not in ("Nomina fija", "Nomina socios"):
            continue
        if not e["activo_julio"] or e.get("liquidado"):
            continue
        sueldos.append({
            "nombre": e["persona"],
            "tipico": round(e.get("base") or e["promedio_mes"], 2),
            "pagado": e["por_mes"].get(mes, 0) > 0,
            "sugerencia": "SUELDO " + e["persona"].upper(),
        })
    sueldos.sort(key=lambda s: (s["pagado"], -s["tipico"]))

    # gasto fijo = categoría con pago en cada uno de los últimos meses
    # completos; el típico es su promedio en esos meses
    completos = an["run_rate"]["meses"]
    fijos = []
    for g in an["gastos"]:
        if g["categoria"] in NO_CHECKLIST:
            continue
        if not all(g["por_mes"].get(m, 0) > 0 for m in completos):
            continue
        fijos.append({
            "nombre": g["categoria"],
            "tipico": round(sum(g["por_mes"][m] for m in completos)
                            / len(completos), 2),
            "pagado": g["por_mes"].get(mes, 0) > 0,
            "sugerencia": SUGERENCIAS.get(g["categoria"], ""),
        })
    fijos.sort(key=lambda s: (s["pagado"], -s["tipico"]))

    cobrar = [{"cliente": c["cliente"], "monto": round(c["pendiente"], 2),
               "atraso": c["cobro"]}
              for c in ta["clientes"] if c.get("pendiente", 0) > 0]
    cobrar.sort(key=lambda x: -x["monto"])

    out = {
        "mes": mes, "mes_nombre": NOMBRES[mes],
        "sueldos": sueldos, "fijos": fijos,
        "por_cobrar": cobrar,
        "por_cobrar_total": round(sum(c["monto"] for c in cobrar), 2),
    }
    json.dump(out, open("app-resumen.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"app-resumen.json · mes {mes} · "
          f"{sum(1 for s in sueldos if not s['pagado'])} sueldos y "
          f"{sum(1 for f in fijos if not f['pagado'])} fijos sin registrar · "
          f"por cobrar {out['por_cobrar_total']:,.2f}")


if __name__ == "__main__":
    main()
