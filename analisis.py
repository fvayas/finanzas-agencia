#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisis de punto de equilibrio y rentabilidad - Agencia 2026
Lee movimientos_2026.json (salida de categorizar.py) y produce:
  - P&L mensual operativo
  - estructura de costos fijos vs variables
  - punto de equilibrio mensual
  - facturacion por cliente y concentracion
  - costo real por persona del equipo
Salida: analisis_2026.json  (consumido por el dashboard)
"""
import json, re
from collections import defaultdict, OrderedDict

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul"]
MES_LARGO = {"ene": "enero", "feb": "febrero", "mar": "marzo", "abr": "abril",
             "may": "mayo", "jun": "junio", "jul": "julio"}


def _limpia(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def motivos(descripciones):
    """Deduce por que el pago de un mes se sale de lo habitual.

    Devuelve una lista de explicaciones en lenguaje llano, a partir de lo que
    dice la propia descripcion del movimiento en la hoja.
    """
    j = " | ".join(_limpia(d) for d in descripciones)
    out = []
    if re.search(r"\bIVA\b", j):
        out.append("emite factura: se le paga el sueldo +15% de IVA")
    if re.search(r"HORA[S]? EXTRA|FERIADO", j):
        det = "horas extras"
        m = re.search(r"PRODUCCION (\w+)", j)
        if m:
            det += f" (producción {m.group(1).title()})"
        elif "FERIADO" in j:
            det += " en feriado"
        out.append(det)
    if re.search(r"MAS TAXIS|Y TAXIS", j):
        out.append("el pago incluye taxis de movilización")
    if "AUMENTO" in j:
        out.append("aumento de sueldo")
    if "DESCUENTO" in j:
        out.append("se le aplicó un descuento")
    if re.search(r"QUINCEN", j):
        out.append("cobra por quincenas, no mensual")
    if re.search(r"PAGO FINAL|ULTIMO MES|ULTIMO PAGO", j):
        out.append("liquidación final: es su último pago")
    if "COMPLETO" in j:
        out.append("pago completo del mes")
    # sueldo de un mes distinto pagado dentro de este
    for corto, largo in MES_LARGO.items():
        if largo.upper() in j:
            out.append(f"incluye el sueldo de {largo}")
            break
    return out

# --- Que es ingreso real de la agencia -------------------------------------
G_INGRESO = ["Ingresos - Fee mensual", "Ingresos - Produccion",
             "Ingresos - Pauta", "Otros ingresos",
             # el dinero entró aunque no sepamos de qué es: cuenta como
             # ingreso, pero queda marcado para revisar
             "Ingresos - Sin identificar"]

# --- Costos FIJOS: existen aunque no entre un cliente mas ------------------
# Karen, Marissa y Josue confirmados como plantilla (entraron may-jun 2026).
# Las pasantias rotan de persona pero la plaza se mantiene: costo fijo.
G_FIJO = ["Nomina fija", "Nomina socios", "Pasantias", "Estructura",
          "Software y herramientas", "Impuestos y legal"]

# --- Costos VARIABLES: escalan con el volumen de trabajo -------------------
G_VARIABLE = ["Nomina variable", "Freelance y produccion", "Pauta",
              "Movilizacion", "Oficina y bienestar", "Equipos",
              "Marketing propio", "Tarjeta de credito", "Devoluciones"]


def main():
    mov = json.load(open("movimientos_2026.json", encoding="utf-8"))
    op = [m for m in mov if m["naturaleza"] == "OPERATIVO"]

    # ---- pauta: dinero del cliente que solo cruza la cuenta ----
    # No es facturacion de la agencia ni gasto propio, asi que sale de los dos
    # lados del P&L. Lo unico que queda como costo real es lo que se adelanto
    # y no se llego a recuperar del cliente.
    try:
        tar = json.load(open("tarifario_2026.json", encoding="utf-8"))
        pauta_in = {mm: round(sum(c["por_mes"][mm]["pauta"]
                                  for c in tar["clientes"]), 2) for mm in MESES}
    except FileNotFoundError:
        tar, pauta_in = None, {mm: 0.0 for mm in MESES}

    # ---------------------------------------------------------------- P&L
    ing_mes = defaultdict(float)
    fijo_mes = defaultdict(float)
    var_mes = defaultdict(float)
    grupo_mes = defaultdict(lambda: defaultdict(float))

    for m in op:
        mes = m["mes"]
        val = m["ingreso"] - m["egreso"]
        grupo_mes[m["grupo"]][mes] += val
        if m["grupo"] in G_INGRESO:
            ing_mes[mes] += val
        elif m["grupo"] in G_FIJO:
            fijo_mes[mes] += -val
        elif m["grupo"] in G_VARIABLE:
            var_mes[mes] += -val

    pl = []
    for mes in MESES:
        i, f, v = ing_mes[mes], fijo_mes[mes], var_mes[mes]
        # se descuenta la pauta de los ingresos y, por el mismo importe, del
        # costo variable. El resultado del mes no cambia; lo que cambia es la
        # base sobre la que se calcula el margen y el punto de equilibrio.
        p_in = pauta_in.get(mes, 0.0)
        p_out = -grupo_mes["Pauta"].get(mes, 0.0)
        i -= p_in                    # cobrar pauta no es facturar
        v -= p_out                   # pagarla no es un gasto propio
        # lo adelantado y aún no recuperado sí es dinero de la agencia.
        # Puede salir negativo un mes: significa que el cliente se puso al día.
        p_neta = p_out - p_in
        coste = f + v + p_neta
        pl.append({
            "mes": mes, "ingresos": round(i, 2),
            "pauta_cobrada": round(p_in, 2), "pauta_pagada": round(p_out, 2),
            "pauta_neta": round(p_neta, 2),
            "costo_fijo": round(f, 2), "costo_variable": round(v, 2),
            "costo_total": round(coste, 2),
            "resultado": round(i - coste, 2),
            "margen_contribucion": round(i - v - p_neta, 2),
            "margen_pct": round((i - v - p_neta) / i * 100, 1) if i else 0.0,
        })

    # ------------------------------------------------ punto de equilibrio
    # Se calcula con el promedio de los 7 meses cerrados.
    n = len(MESES)
    ing_prom = sum(p["ingresos"] for p in pl) / n
    fijo_prom = sum(p["costo_fijo"] for p in pl) / n
    # la pauta no recuperada entra como variable: crece con el volumen de pauta
    var_prom = sum(p["costo_variable"] + p["pauta_neta"] for p in pl) / n
    ratio_var = var_prom / ing_prom if ing_prom else 0        # % variable
    mc_ratio = 1 - ratio_var                                  # margen contrib.
    breakeven = fijo_prom / mc_ratio if mc_ratio > 0 else 0

    # punto de equilibrio sin contar el sueldo de los socios
    socios_prom = -sum(grupo_mes["Nomina socios"].values()) / n
    be_sin_socios = ((fijo_prom - socios_prom) / mc_ratio) if mc_ratio > 0 else 0

    # --------------------------------------------------------- clientes
    cli_mes = defaultdict(lambda: defaultdict(float))
    cli_tot = defaultdict(float)
    cli_pagos = defaultdict(int)
    for m in op:
        if m["grupo"] not in ("Ingresos - Fee mensual", "Ingresos - Produccion"):
            continue
        # el nombre del cliente vive en 'categoria' (fee) o 'detalle' (produccion)
        cli = m["categoria"] if m["grupo"] == "Ingresos - Fee mensual" \
            else (m["detalle"] or "Sin identificar")
        cli_mes[cli][m["mes"]] += m["ingreso"] - m["egreso"]
        cli_tot[cli] += m["ingreso"] - m["egreso"]
        cli_pagos[cli] += 1

    clientes = []
    total_cli = sum(cli_tot.values())
    for c, t in sorted(cli_tot.items(), key=lambda x: -x[1]):
        meses_act = [mm for mm in MESES if abs(cli_mes[c][mm]) > 0.01]
        clientes.append({
            "cliente": c, "total": round(t, 2),
            "pct": round(t / total_cli * 100, 1) if total_cli else 0,
            # nº de giros recibidos, que no coincide con los meses activos:
            # hay meses con dos cobros y meses sin ninguno
            "pagos": cli_pagos[c],
            "meses_activo": len(meses_act),
            "primer_mes": meses_act[0] if meses_act else "",
            "ultimo_mes": meses_act[-1] if meses_act else "",
            "fee_promedio": round(t / len(meses_act), 2) if meses_act else 0,
            "por_mes": {mm: round(cli_mes[c][mm], 2) for mm in MESES},
        })

    # concentracion: cuanto pesan los 3 y los 5 mayores
    tops = [c["pct"] for c in clientes]
    conc = {"top1": round(sum(tops[:1]), 1), "top3": round(sum(tops[:3]), 1),
            "top5": round(sum(tops[:5]), 1)}

    # ----------------------------------------------------------- equipo
    pers_mes = defaultdict(lambda: defaultdict(float))
    pers_det = defaultdict(lambda: defaultdict(list))   # movimientos crudos
    pers_tipo = {}
    for m in op:
        if m["grupo"] not in ("Nomina fija", "Nomina socios", "Nomina variable",
                              "Pasantias"):
            continue
        # en nomina fija/socios/pasantias el nombre esta en 'categoria';
        # en horas extras esta en 'detalle', y a veces no hay nombre
        if m["categoria"] != "Horas extras":
            nom = m["categoria"]
        else:
            det = (m["detalle"] or "").strip()
            # 'detalle' solo es un nombre si son 2-3 palabras sin verbos de pago
            es_nombre = det and len(det.split()) <= 3 and \
                not any(w in det.upper() for w in ("PAGO", "SUELDO", "HORAS"))
            nom = det if es_nombre else "Horas extras sin asignar"
        pers_mes[nom][m["mes"]] += m["egreso"]
        pers_det[nom][m["mes"]].append({
            "fecha": m["fecha"], "importe": round(m["egreso"], 2),
            "desc": m["descripcion"],
        })
        pers_tipo[nom] = m["grupo"]

    equipo = []
    for p, meses in sorted(pers_mes.items(),
                           key=lambda x: -sum(x[1].values())):
        act = [mm for mm in MESES if meses[mm] > 0.01]
        tot = sum(meses.values())

        # ---- ficha explicativa de cada mes ----
        # base = el importe mensual que mas se repite; sirve de referencia
        vals = [round(meses[mm], 2) for mm in act]
        base = max(set(vals), key=vals.count) if vals else 0.0
        # La base es el sueldo VIGENTE. Comparar contra ella los meses previos
        # a una subida (o a que empezara a facturar) da diferencias enormes que
        # no explican nada, asi que solo se compara desde que la base aparece.
        i_base = next((i for i, mm in enumerate(act)
                       if abs(meses[mm] - base) < 1.0), 0)
        detalle = {}
        razones_prev = []
        for idx, mm in enumerate(act):
            movs = sorted(pers_det[p][mm], key=lambda d: d["fecha"])
            razones = motivos([d["desc"] for d in movs])
            # dos pagos del importe completo = el sueldo de un mes salio tarde
            dos_sueldos = (len(movs) == 2 and base > 0 and
                           all(abs(mv["importe"] - base) < 1 for mv in movs))
            liquida = any("liquidación" in r for r in razones)
            if dos_sueldos and liquida:
                # dos pagos iguales pero uno es el finiquito: no es un retraso
                razones.insert(0, "el mes lleva el sueldo normal y la liquidación")
            elif dos_sueldos:
                # el mes que quedo sin cobrar es el anterior del calendario,
                # no el anterior en que hubo pago (justamente ese mes es el vacio)
                i_cal = MESES.index(mm)
                anterior = MES_LARGO[MESES[i_cal - 1]] if i_cal > 0 else "el mes anterior"
                razones = [f"se pagaron dos sueldos en el mismo mes: "
                           f"en {anterior} no se cobró y salió con retraso"]
            elif len(movs) > 1 and not razones:
                razones.append(f"se pagó en {len(movs)} partes durante el mes")
            # variacion respecto al mes anterior en que cobro.
            # Todo lo que sigue solo aplica si el importe cambio de verdad:
            # una diferencia de centimos no es un hecho que explicar.
            delta = None
            if idx > 0 and abs(meses[mm] - meses[act[idx - 1]]) > 0.5:
                prev = act[idx - 1]
                ant, act_v = meses[prev], meses[mm]
                dif = act_v - ant
                delta = {"vs": prev, "dif": round(dif, 2)}
                prev_txt = " ".join(razones_prev)

                # el salto de 15% exacto delata que empieza o deja de facturar.
                # La descripcion no siempre lo dice, pero el importe si.
                if abs(act_v - ant * 1.15) < 1.0 and "IVA" not in " ".join(razones):
                    razones.insert(0, "empieza a facturar: mismo sueldo +15% de IVA")
                elif abs(act_v - ant / 1.15) < 1.0:
                    razones.insert(0, "deja de facturar: vuelve al sueldo sin IVA")

                # el mes anterior llevaba algo extra y este baja
                if not razones and dif < 0:
                    if "dos sueldos" in prev_txt or "sueldo de" in prev_txt:
                        razones.append("el mes anterior llevaba dos sueldos; "
                                       "este es un mes normal")
                    elif razones_prev and abs(act_v - base) < 1.0:
                        razones.append("vuelve a su sueldo habitual: "
                                       "el mes anterior llevaba extras")
                    elif abs(act_v - base) < 1.0:
                        razones.append("vuelve a su sueldo habitual")

                if not razones and abs(dif) <= 15:
                    razones.append("ajuste menor: redondeo o días trabajados")
                if not razones:
                    razones.append("baja de sueldo" if dif < 0 else "sube el sueldo")
            detalle[mm] = {
                "movs": movs, "razones": razones, "delta": delta,
                "vs_base": round(meses[mm] - base, 2),
                "cmp_base": idx >= i_base and len(act) >= 3,
            }
            razones_prev = razones

        equipo.append({
            "persona": p, "grupo": pers_tipo[p], "total": round(tot, 2),
            "meses": len(act),
            "promedio_mes": round(tot / len(act), 2) if act else 0,
            # con menos de 3 meses cobrados no hay un sueldo "habitual" fiable
            "base": round(base, 2) if len(act) >= 3 else None,
            "primer_mes": act[0] if act else "", "ultimo_mes": act[-1] if act else "",
            "activo_julio": "jul" in act,
            # cobró en julio pero fue su finiquito: sale de plantilla en agosto
            "liquidado": bool(act) and any(
                "liquidación" in r for r in detalle[act[-1]]["razones"]),
            "por_mes": {mm: round(meses[mm], 2) for mm in MESES},
            "detalle": detalle,
        })

    # ------------------------------- todo lo que no es nómina ni cobro
    # El tercer bloque del flujo: arriendo, servicios, software, producción,
    # impuestos, tarjeta... Se agrupa por categoría y se guarda el detalle
    # para poder abrir cada celda y ver los movimientos que la componen.
    G_NOMINA = {"Nomina fija", "Nomina socios", "Nomina variable", "Pasantias"}
    G_COBRO = set(G_INGRESO)

    gm = defaultdict(lambda: defaultdict(float))
    gd = defaultdict(lambda: defaultdict(list))
    for m in mov:
        if m["grupo"] in G_NOMINA or m["grupo"] in G_COBRO:
            continue
        if m["grupo"] == "Saldo Inicial":
            continue
        clave = (m["grupo"], m["categoria"])
        val = m["egreso"] - m["ingreso"]          # positivo = sale dinero
        gm[clave][m["mes"]] += val
        gd[clave][m["mes"]].append({
            "fecha": m["fecha"], "desc": m["descripcion"],
            "importe": round(val, 2),
        })

    gastos = []
    for (grupo, categoria), meses in sorted(
            gm.items(), key=lambda x: -abs(sum(x[1].values()))):
        det = {}
        for mm in MESES:
            movs = sorted(gd[(grupo, categoria)][mm], key=lambda d: d["fecha"])
            if movs:
                det[mm] = {"movs": movs, "razones": []}
        gastos.append({
            "grupo": grupo, "categoria": categoria,
            "total": round(sum(meses.values()), 2),
            "n": sum(len(v["movs"]) for v in det.values()),
            "por_mes": {mm: round(meses[mm], 2) for mm in MESES},
            "detalle": det,
        })

    # -------------------- ingresos que no vienen de una cuenta --------------
    # Subarriendo de la oficina, intereses del banco y cobros sueltos. Entraban
    # en el total del P&L pero no salian en ninguna tabla: quedaban invisibles.
    # los cobros sin identificar ya salen en la tabla de clientes: aquí
    # sólo lo que no tiene ninguna otra tabla donde verse
    G_OTROS = ["Otros ingresos"]
    om = defaultdict(lambda: defaultdict(float))
    od = defaultdict(lambda: defaultdict(list))
    for m in op:
        if m["grupo"] not in G_OTROS:
            continue
        # el subarriendo se separa por inquilino; el resto por concepto
        clave = (f"{m['categoria']} · {m['detalle']}"
                 if m["categoria"] == "Subarriendo oficina" and m["detalle"]
                 else m["categoria"])
        val = m["ingreso"] - m["egreso"]
        om[clave][m["mes"]] += val
        od[clave][m["mes"]].append({
            "fecha": m["fecha"], "desc": m["descripcion"],
            "importe": round(val, 2)})

    otros_ing = []
    for clave, meses in sorted(om.items(), key=lambda x: -sum(x[1].values())):
        det = {mm: {"movs": sorted(od[clave][mm], key=lambda d: d["fecha"]),
                    "razones": []}
               for mm in MESES if od[clave][mm]}
        otros_ing.append({
            "concepto": clave,
            "total": round(sum(meses.values()), 2),
            "n": sum(len(v["movs"]) for v in det.values()),
            "por_mes": {mm: round(meses[mm], 2) for mm in MESES},
            "detalle": det,
        })

    # ------------------------------------------------- run-rate actual
    # Ultimos 3 meses cerrados (may, jun, jul) = foto mas realista de hoy
    ult = pl[-3:]
    rr = {
        "ingresos": round(sum(p["ingresos"] for p in ult) / 3, 2),
        "costo_fijo": round(sum(p["costo_fijo"] for p in ult) / 3, 2),
        "costo_variable": round(sum(p["costo_variable"] + p["pauta_neta"]
                                    for p in ult) / 3, 2),
        "resultado": round(sum(p["resultado"] for p in ult) / 3, 2),
    }
    rr["ratio_variable"] = round(rr["costo_variable"] / rr["ingresos"], 4) \
        if rr["ingresos"] else 0
    rr["mc_ratio"] = round(1 - rr["ratio_variable"], 4)
    rr["breakeven"] = round(rr["costo_fijo"] / rr["mc_ratio"], 2) \
        if rr["mc_ratio"] > 0 else 0
    rr["holgura"] = round(rr["ingresos"] - rr["breakeven"], 2)

    # ------------------------------------------------------ no operativo
    noop = defaultdict(lambda: defaultdict(float))
    for m in mov:
        if m["naturaleza"] == "NO OPERATIVO":
            noop[m["grupo"]][m["mes"]] += m["ingreso"] - m["egreso"]

    out = {
        "meses": MESES,
        "pl": pl,
        "grupos": {g: {mm: round(v[mm], 2) for mm in MESES}
                   for g, v in grupo_mes.items()},
        "no_operativo": {g: {mm: round(v[mm], 2) for mm in MESES}
                         for g, v in noop.items()},
        "promedios": {
            "ingresos": round(ing_prom, 2), "costo_fijo": round(fijo_prom, 2),
            "costo_variable": round(var_prom, 2),
            "ratio_variable": round(ratio_var, 4),
            "mc_ratio": round(mc_ratio, 4),
            "breakeven": round(breakeven, 2),
            "breakeven_sin_socios": round(be_sin_socios, 2),
            "sueldo_socios": round(socios_prom, 2),
        },
        "run_rate": rr,
        # el panel necesita saber qué grupos componen cada línea del P&L
        "familias": {"ingreso": G_INGRESO, "fijo": G_FIJO, "variable": G_VARIABLE},
        "clientes": clientes,
        "concentracion": conc,
        "equipo": equipo,
        "gastos": gastos,
        "otros_ingresos": otros_ing,
        "totales": {
            "ingresos": round(sum(p["ingresos"] for p in pl), 2),
            "costo_fijo": round(sum(p["costo_fijo"] for p in pl), 2),
            "costo_variable": round(sum(p["costo_variable"] for p in pl), 2),
            "resultado": round(sum(p["resultado"] for p in pl), 2),
            "movimientos": len(mov),
        },
    }
    json.dump(out, open("analisis_2026.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ------------------------------------------------------------ consola
    W = 11
    print("=" * 86)
    print("P&L OPERATIVO 2026  (enero - julio)")
    print("=" * 86)
    print(f"{'':<24}" + "".join(f"{mm:>{W}}" for mm in MESES) + f"{'TOTAL':>13}")
    for k, lab in [("ingresos", "INGRESOS (sin pauta)"),
                   ("costo_fijo", "Costo fijo"),
                   ("costo_variable", "Costo variable"),
                   ("pauta_neta", "Pauta no recuperada"),
                   ("costo_total", "Costo total"), ("resultado", "RESULTADO")]:
        fila = "".join(f"{p[k]:>{W},.0f}" for p in pl)
        print(f"{lab:<24}{fila}{sum(p[k] for p in pl):>13,.0f}")
    print(f"{'Margen contrib. %':<24}" +
          "".join(f"{p['margen_pct']:>{W},.1f}" for p in pl))

    pr, r = out["promedios"], out["run_rate"]
    print()
    print("=" * 86)
    print("PUNTO DE EQUILIBRIO")
    print("=" * 86)
    print(f"{'':<38}{'promedio 7m':>16}{'run-rate 3m':>16}")
    print(f"{'Ingresos / mes':<38}{pr['ingresos']:>16,.0f}{r['ingresos']:>16,.0f}")
    print(f"{'Costo fijo / mes':<38}{pr['costo_fijo']:>16,.0f}{r['costo_fijo']:>16,.0f}")
    print(f"{'Costo variable / mes':<38}{pr['costo_variable']:>16,.0f}{r['costo_variable']:>16,.0f}")
    print(f"{'Costo variable como % de ingresos':<38}"
          f"{pr['ratio_variable']*100:>15,.1f}%{r['ratio_variable']*100:>15,.1f}%")
    print(f"{'Margen de contribucion':<38}"
          f"{pr['mc_ratio']*100:>15,.1f}%{r['mc_ratio']*100:>15,.1f}%")
    print("-" * 70)
    print(f"{'>> PUNTO DE EQUILIBRIO / mes':<38}"
          f"{pr['breakeven']:>16,.0f}{r['breakeven']:>16,.0f}")
    print(f"{'   Holgura sobre el equilibrio':<38}"
          f"{pr['ingresos']-pr['breakeven']:>16,.0f}{r['holgura']:>16,.0f}")
    print(f"{'   Equilibrio si los socios no cobran':<38}"
          f"{pr['breakeven_sin_socios']:>16,.0f}")

    print()
    print("=" * 86)
    print("FACTURACION POR CLIENTE")
    print("=" * 86)
    print(f"{'CLIENTE':<24}{'TOTAL':>12}{'%':>7}{'meses':>7}{'fee/mes':>11}  ultimo")
    for c in clientes:
        print(f"{c['cliente']:<24}{c['total']:>12,.0f}{c['pct']:>7,.1f}"
              f"{c['meses_activo']:>7}{c['fee_promedio']:>11,.0f}  {c['ultimo_mes']}")
    print(f"\nConcentracion -> top1 {conc['top1']}% | top3 {conc['top3']}% | "
          f"top5 {conc['top5']}%")

    print()
    print("=" * 86)
    print("COSTO DEL EQUIPO")
    print("=" * 86)
    print(f"{'PERSONA':<26}{'TIPO':<18}{'TOTAL':>11}{'meses':>7}{'prom/mes':>11}  activo jul")
    for e in equipo:
        print(f"{e['persona']:<26}{e['grupo'].replace('Nomina ',''):<18}"
              f"{e['total']:>11,.0f}{e['meses']:>7}{e['promedio_mes']:>11,.0f}"
              f"   {'si' if e['activo_julio'] else 'NO'}")
    print(f"\nCosto total de nomina 7 meses: "
          f"{sum(e['total'] for e in equipo):,.0f}")


if __name__ == "__main__":
    main()
