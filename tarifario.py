#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarifario de honorarios y reconciliacion con lo cobrado en banco.

Separa, para cada cuenta, tres cosas que hoy van mezcladas en la hoja:
  HONORARIO -> el fee contratado (lo que realmente factura la agencia)
  PAUTA     -> dinero del cliente que solo pasa por la cuenta rumbo a Meta/Google
  PUNTUAL   -> proyectos sueltos (web, branding, produccion, eventos)

Y explica la diferencia entre lo facturado y lo cobrado: las retenciones.

Retenciones detectadas en Ecuador para esta agencia:
  IR   3%  sobre el honorario  (servicios de publicidad y comunicacion)
  IVA  70% o 100% del IVA, segun si el cliente es contribuyente especial
Se validan al centavo contra Flota Imbabura, Speedy, El Motor y Plasticaucho.

Salida: tarifario_2026.json
"""
import json, re
from collections import defaultdict

IVA = 0.15
# meses derivados de los datos: la columna de agosto nace con su primer registro
BASE12 = ["ene", "feb", "mar", "abr", "may", "jun", "jul",
          "ago", "sep", "oct", "nov", "dic"]
import json as _json
_mov0 = _json.load(open("movimientos_2026.json", encoding="utf-8"))
MESES = BASE12[:max(BASE12.index(m["mes"]) for m in _mov0
                    if m["mes"] in BASE12) + 1]

# --------------------------------------------------------------------------
# TARIFARIO — confirmado por Francisco (julio 2026)
#
#   fee        honorario mensual contratado, ANTES de IVA
#   iva        True si al fee se le suma el 15%
#   ret_ir     retencion de impuesto a la renta sobre el fee
#   ret_iva    porcion del IVA que retiene el cliente
#   desde      cambios de tarifa: {mes: nuevo_fee}
#   estado     activo | cerrado | puntual | variable
# --------------------------------------------------------------------------
TARIFARIO = {
    # entro en mayo pero su primer giro es de junio y no declara periodo:
    # sin 'inicio' el conteo creeria que empezo a devengar en junio
    "Speedy":         dict(fee=2400, iva=True,  ret_ir=.03, ret_iva=.70, estado="activo",
                           inicio="may"),
    "Uninova":        dict(fee=900,  iva=False, ret_ir=0,   ret_iva=0,   estado="activo"),
    "Fiammingo":      dict(fee=800,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo"),
    # paga el fee y la pauta en un solo giro: el exceso sobre el fee es pauta.
    # Baja de 700 a 600 a partir de julio (confirmado por Francisco, jul 2026).
    "Healthy Girl":   dict(fee=700,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo",
                           desde={"jul": 600}, exceso="pauta"),
    "El Motor":       dict(fee=650,  iva=True,  ret_ir=0,   ret_iva=1.0, estado="activo"),
    # Samari retiene, pero las tasas no encajan en un porcentaje unico
    # (2,88% del facturado en el tramo de 600 y 3,51% en el de 650). Hasta
    # tener el comprobante, se usa el neto observado, que si es exacto.
    "Samari":         dict(fee=600,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo",
                           desde={"may": 650}, neto={600: 670.13, 650: 721.23},
                           nota_puntual="lo que pasa del fee es pago de modelos "
                                        "y viáticos de producción",
                           inferido="retención calculada desde los pagos reales; "
                                    "faltan los porcentajes del comprobante"),
    # 640 liquidos = 640 + IVA con el 100% del IVA retenido. Subio a 700 en abril.
    "Velsana":        dict(fee=640,  iva=True,  ret_ir=0,   ret_iva=1.0, estado="activo",
                           desde={"abr": 700}),
    "Flota Imbabura": dict(fee=550,  iva=True,  ret_ir=.03, ret_iva=.70, estado="activo"),
    "APC":            dict(fee=500,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo"),
    "Cigarra":        dict(fee=450,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo"),
    "Confia":         dict(fee=450,  iva=True,  ret_ir=0,   ret_iva=1.0, estado="activo",
                           desde={"may": 500}),   # subida confirmada
    "Nane Vestidos":  dict(fee=450,  iva=False, ret_ir=0,   ret_iva=0,   estado="activo"),
    "Casa del Verde": dict(fee=430,  iva=False, ret_ir=0,   ret_iva=0,   estado="activo"),
    "Pladeco":        dict(fee=350,  iva=True,  ret_ir=0,   ret_iva=1.0, estado="activo",
                           desde={"mar": 400}, exceso="pauta"),
    "Plasticaucho":   dict(fee=350,  iva=True,  ret_ir=.03, ret_iva=1.0, estado="activo"),
    "Pasteur":        dict(fee=400,  iva=False, ret_ir=0,   ret_iva=0,   estado="cerrado"),
    "Tartelier":      dict(fee=300,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo"),
    "Chiflido":       dict(fee=300,  iva=False, ret_ir=0,   ret_iva=0,   estado="activo"),
    "Onco Ambato":    dict(fee=300,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo"),
    "Absolute":       dict(fee=300,  iva=False, ret_ir=0,   ret_iva=0,   estado="activo"),
    "Provita":        dict(fee=250,  iva=True,  ret_ir=0,   ret_iva=0,   estado="activo"),
    "MM Wings":       dict(fee=135,  iva=False, ret_ir=0,   ret_iva=0,   estado="activo"),
    # ingresos que no son honorario de agencia
    # paga dos cosas distintas: $120 de fee y $70 de arriendo del puesto.
    # El arriendo va aparte, en "Otros ingresos", no aquí.
    "Friends Guides": dict(fee=120, iva=False, ret_ir=0, ret_iva=0, estado="activo"),
    "Tienda Electro": dict(fee=None, iva=False, ret_ir=0, ret_iva=0, estado="variable",
                           nota="pago variable, se toma el neto"),
    "La Tartuca":     dict(fee=None, iva=False, ret_ir=0, ret_iva=0, estado="puntual",
                           nota="trabajo único de branding"),
    "Victor Hugo (evento)": dict(fee=None, iva=False, ret_ir=0, ret_iva=0, estado="puntual",
                           nota="evento puntual"),
    "Dog Spa":        dict(fee=None, iva=False, ret_ir=0, ret_iva=0, estado="puntual",
                           nota="trabajo puntual de video"),
    "Nicris":         dict(fee=None, iva=False, ret_ir=0, ret_iva=0, estado="puntual",
                           nota="reposición de una luz rota, no es facturación"),
    "Nono":           dict(fee=450,  iva=False, ret_ir=0, ret_iva=0, estado="cerrado"),
}

# --------------------------------------------------------------------------
# Giros que traen el pago de dos cuentas juntas. Sin esto, el importe entero
# se le atribuye a quien encabeza la descripcion y la otra cuenta desaparece.
#   (fecha, fragmento, {cliente: importe})
# --------------------------------------------------------------------------
SPLITS = [
    ("23/02/2026", "VELSANA DEL 11 DE ENERO",
     {"Velsana": 640.00, "Pasteur": 495.00}),
]

# Conceptos que NO son honorario aunque lleguen del cliente
PAUTA_KW   = ("PAUTA",)
PUNTUAL_KW = ("WEB", "BRANDING", "PRODUCCION", "ACTORES", "VIDEO", "PODCAST",
              "EVENTO", "ENTRADAS", "FIESTA", "MODELO", "VIATICOS", "RODAJE",
              "CRM", "MONDAY", "LUCES", "FOTOS")


def esperado(cfg, mes):
    """Fee vigente ese mes, lo facturado con IVA y lo que deberia llegar al banco."""
    fee = cfg["fee"]
    if fee is None:
        return None
    for m_cambio, nuevo in (cfg.get("desde") or {}).items():
        if MESES.index(mes) >= MESES.index(m_cambio):
            fee = nuevo
    iva = fee * IVA if cfg["iva"] else 0.0
    facturado = fee + iva
    # si conocemos el neto que realmente llega, manda ese dato sobre la formula
    neto = (cfg.get("neto") or {}).get(fee)
    retenido = (facturado - neto) if neto is not None \
        else fee * cfg["ret_ir"] + iva * cfg["ret_iva"]
    return {"fee": round(fee, 2), "iva": round(iva, 2),
            "facturado": round(facturado, 2),
            "retenido": round(retenido, 2),
            "a_cobrar": round(facturado - retenido, 2)}


MES_LARGO = {"ene": "enero", "feb": "febrero", "mar": "marzo", "abr": "abril",
             "may": "mayo", "jun": "junio", "jul": "julio", "ago": "agosto",
             "sep": "septiembre", "oct": "octubre", "nov": "noviembre",
             "dic": "diciembre"}

# Mes EXIGIBLE: el ultimo mes ya terminado a la fecha del ultimo movimiento.
# Con datos al 3 de agosto, deber agosto no es deber nada; se debe hasta julio.
# El dia 31 de un mes, ese mes ya cuenta como terminado.
import calendar as _cal
_d, _m, _a = (int(x) for x in _mov0[-1]["fecha"].split("/"))
MES_CORTE = _m if _d == _cal.monthrange(_a, _m)[1] else _m - 1

# Nombres de mes tal y como aparecen escritos en la hoja, con sus erratas.
# El orden importa: primero las formas largas para que "DICEMBRE" no case
# con un patron mas corto.
MESES_TXT = [
    (r"DICI?E?MBRE", 12), (r"NOVIE?MBRE", 11), (r"OCTUBRE", 10),
    (r"SEPTIEMBRE|SETIEMBRE", 9), (r"AGOSTO", 8),
    (r"JULIO|D\s*EJULIO", 7), (r"JUNIO", 6), (r"MAYO|D\s*EMAYO", 5),
    (r"ABRIL|ABIL", 4), (r"MARZO", 3), (r"FEBRE?O|FEBRERO", 2), (r"ENERO", 1),
]


def periodo_cubierto(desc, mes_pago):
    """Ultimo mes de servicio que cubre un pago, leyendo su descripcion.

    "DEL 18 DE JUNIO AL 18 DE JULIO" -> 7      (periodo, manda el mes final)
    "PAGO SAMARI JUNIO"              -> 6      (un solo mes)
    Devuelve None si la descripcion no dice a que periodo corresponde.
    """
    d = (desc or "").upper()
    encontrados = []
    for pat, num in MESES_TXT:
        for m in re.finditer(pat, d):
            encontrados.append((m.start(), num))
    if not encontrados:
        return None
    encontrados.sort()                       # por orden de aparicion
    ultimo = encontrados[-1][1]
    # un pago de enero que menciona diciembre cubre el diciembre anterior:
    # se normaliza a 0 para que no parezca adelantado once meses
    if ultimo - mes_pago > 6:
        ultimo -= 12
    return ultimo


def motivos_mes(movs, esp, activo_antes, activo_despues, cfg=None):
    """Por que el cobro de un mes se sale de la tarifa. Lenguaje llano."""
    if not movs:
        if activo_antes and activo_despues:
            return ["no hubo cobro este mes; se regularizó en otro"]
        if activo_antes:
            return ["dejó de cobrarse a partir de aquí"]
        return ["todavía no era cliente"]

    r = []
    hon = sum(m["honorario"] for m in movs)
    pau = sum(m["pauta"] for m in movs)
    pun = sum(m["puntual"] for m in movs)

    k = 0
    if esp and esp["a_cobrar"]:
        k = round(hon / esp["a_cobrar"])
        if k >= 2 and abs(hon - k * esp["a_cobrar"]) <= 2:
            r.append(f"cobró {k} mensualidades en el mismo mes")
    if pau > 0:
        r.append("el giro trae pauta del cliente, que no es facturación")
    if pun > 0:
        # algunas cuentas siempre facturan el mismo tipo de extra; decir cuál
        # es más útil que un genérico "trabajo puntual"
        r.append((cfg or {}).get("nota_puntual")
                 or "incluye un trabajo puntual facturado aparte del fee")
    if len(movs) > 1 and not r:
        r.append(f"llegó en {len(movs)} giros distintos")

    if esp and esp["a_cobrar"] and k < 2:
        d = hon - esp["a_cobrar"]
        if abs(d) > max(20, esp["a_cobrar"] * .04):
            r.append("cobró de más sobre su tarifa" if d > 0
                     else "cobró por debajo de su tarifa")
    return r


def clasifica_pago(desc, cliente):
    """honorario | pauta | puntual, mirando lo que dice la descripcion."""
    d = (desc or "").upper()
    if any(k in d for k in PAUTA_KW):
        # "fee mensual mas pautas" lleva las dos cosas
        return "mixto" if ("FEE" in d or "MENSUAL" in d) else "pauta"
    if any(k in d for k in PUNTUAL_KW):
        return "puntual"
    return "honorario"


def main():
    mov = json.load(open("movimientos_2026.json", encoding="utf-8"))
    ing = [m for m in mov if m["ingreso"] > 0 and m["grupo"].startswith("Ingresos")]

    pagos = defaultdict(list)
    for m in ing:
        cli = (m["categoria"] if m["grupo"] == "Ingresos - Fee mensual"
               else (m["detalle"] or "Sin identificar"))
        # un giro que paga dos cuentas se reparte antes de agrupar
        rep = next((r for f, frag, r in SPLITS
                    if m["fecha"] == f and frag in m["descripcion"].upper()), None)
        if rep:
            for c, imp in rep.items():
                pagos[c].append({**m, "ingreso": imp,
                                 "descripcion": f"{m['descripcion']} [parte de {c}]"})
            continue
        pagos[cli].append(m)

    fichas, avisos = [], []
    for cli, lst in sorted(pagos.items(), key=lambda x: -sum(p["ingreso"] for p in x[1])):
        cfg = TARIFARIO.get(cli)
        cobrado = sum(p["ingreso"] for p in lst)
        if not cfg:
            avisos.append(f"{cli}: no está en el tarifario (cobrado {cobrado:,.2f})")
            cfg = dict(fee=None, iva=False, ret_ir=0, ret_iva=0,
                       estado="sin tarifa", nota="falta confirmar tarifa")

        # reparto de cada pago
        rep = {"honorario": 0.0, "pauta": 0.0, "puntual": 0.0}
        por_mes = defaultdict(lambda: {"honorario": 0.0, "pauta": 0.0,
                                       "puntual": 0.0, "cobrado": 0.0})
        detalle = []
        for p in sorted(lst, key=lambda x: (MESES.index(x["mes"]), x["fecha"])):
            tipo = clasifica_pago(p["descripcion"], cli)
            esp = esperado(cfg, p["mes"])
            imp = p["ingreso"]
            hon = pau = pun = 0.0
            if tipo == "puntual":
                pun = imp
            elif tipo == "pauta":
                pau = imp
            elif tipo == "mixto" and esp:
                hon = min(imp, esp["a_cobrar"]); pau = imp - hon
            elif esp and any(abs(imp - k * esp["a_cobrar"]) <= 2 for k in (2, 3, 4)):
                # multiplo exacto del fee: son varias mensualidades juntas,
                # todo honorario. Sin esto se leeria como fee + trabajo extra.
                hon = imp
            elif esp and imp > esp["a_cobrar"] + max(20, esp["a_cobrar"] * .03):
                # cobra mas que su fee. En las cuentas que pagan la pauta dentro
                # del mismo giro el exceso es pauta; en el resto son trabajos
                # extra facturados aparte.
                hon = esp["a_cobrar"]
                if cfg.get("exceso", "puntual") == "pauta":
                    pau = imp - hon
                else:
                    pun = imp - hon
            else:
                hon = imp
            rep["honorario"] += hon; rep["pauta"] += pau; rep["puntual"] += pun
            pm = por_mes[p["mes"]]
            pm["honorario"] += hon; pm["pauta"] += pau
            pm["puntual"] += pun; pm["cobrado"] += imp
            detalle.append({
                "mes": p["mes"], "fecha": p["fecha"], "desc": p["descripcion"],
                "importe": round(imp, 2), "tipo": tipo,
                "honorario": round(hon, 2), "pauta": round(pau, 2),
                "puntual": round(pun, 2),
                "esperado": esp["a_cobrar"] if esp else None,
                "desvio": round(imp - esp["a_cobrar"], 2) if (esp and tipo == "honorario") else None,
            })

        # meses en que cobro honorario y cuadre contra lo esperado
        meses_hon = [mm for mm in MESES if por_mes[mm]["honorario"] > 0.01]
        cuadra, desvios, dobles = True, [], []
        for mm in meses_hon:
            esp = esperado(cfg, mm)
            if not esp:
                cuadra = None; break
            real = por_mes[mm]["honorario"]
            d = real - esp["a_cobrar"]
            # margen de ruido: redondeos, comisiones y ajustes de dias. Marcar
            # un desvio de $6 como incidencia solo esconde las de verdad.
            if abs(d) <= max(20, esp["a_cobrar"] * .04):
                continue
            # cobrar 2 o 3 mensualidades en el mismo mes no es un descuadre:
            # es un cliente que se puso al día o que pagó adelantado.
            k = next((k for k in (2, 3, 4)
                      if abs(real - k * esp["a_cobrar"]) <= 2), None)
            if k:
                dobles.append({"mes": mm, "n": k})
                continue
            cuadra = False
            desvios.append({"mes": mm, "dif": round(d, 2),
                            "esperado": esp["a_cobrar"],
                            "real": round(real, 2)})

        # ---- ficha mensual para el panel: movimientos + por que ----
        activos = [mm for mm in MESES if por_mes[mm]["cobrado"] > 0.01]
        ficha_mes = {}
        for mm in MESES:
            movs = [d for d in detalle if d["mes"] == mm]
            antes = any(x in activos for x in MESES[:MESES.index(mm)])
            despues = any(x in activos for x in MESES[MESES.index(mm) + 1:])
            esp_mm = esperado(cfg, mm)
            ficha_mes[mm] = {
                "movs": movs,
                "razones": motivos_mes(movs, esp_mm, antes, despues, cfg),
                "esperado": esp_mm["a_cobrar"] if esp_mm else None,
            }

        # ------------------- ¿estamos al día con esta cuenta? -------------------
        # Señal principal: hasta qué mes de servicio llega el último pago, leído
        # de su propia descripción. Si no la dice, se cae al conteo de cuántas
        # mensualidades se han cobrado frente a las que tocaba cobrar.
        con_hon = [d for d in detalle if d["honorario"] > 0]
        periodos = [periodo_cubierto(d["desc"], MESES.index(d["mes"]) + 1)
                    for d in con_hon]
        # si algun cobro de fee no dice a que mes corresponde, la cadena de
        # periodos esta rota y el ultimo declarado se queda corto
        cadena_completa = bool(periodos) and all(p is not None for p in periodos)

        cubierto_periodo = periodos[-1] if periodos else None

        atraso_meses = cubierto_conteo = None
        if cfg["fee"] is not None and con_hon:
            # primer mes de SERVICIO, no del primer cobro: quien paga vencido
            # empieza a cobrar despues de empezar a devengar. El valor puede ser
            # <= 0 si el primer cobro cubria meses del año anterior.
            # 'inicio' manda: es un dato del contrato, no una deduccion
            if cfg.get("inicio"):
                primer_serv = MESES.index(cfg["inicio"]) + 1
            else:
                primer_serv = next((p for p in periodos if p is not None), None)
            if primer_serv is None:
                primer_serv = MESES.index(activos[0]) + 1
            devengados = MES_CORTE - primer_serv + 1
            fee_ref = esperado(cfg, "jul")["a_cobrar"]
            pagados = rep["honorario"] / fee_ref if fee_ref else 0
            atraso_meses = round(devengados - pagados, 1)
            cubierto_conteo = MES_CORTE - round(atraso_meses)

        # Manda lo que declara el último cobro: es verificable en la propia
        # hoja. El conteo solo entra cuando no hay periodo declarado, porque
        # se descuadra en cuanto un cobro antiguo cubrió meses del año anterior.
        if cubierto_periodo is not None:
            cubierto = cubierto_periodo
            fuente = "periodo declarado en el último cobro"
            if not cadena_completa:
                fuente += "; ojo, algún cobro anterior no declara mes"
        else:
            cubierto = cubierto_conteo
            fuente = "mensualidades cobradas frente a las devengadas"

        # cuando los dos métodos discrepan, conviene decirlo en vez de elegir
        nota = ""
        if (cubierto_periodo is not None and cubierto_conteo is not None
                and abs(cubierto_periodo - cubierto_conteo) >= 1):
            nota = (f"lecturas distintas: el último cobro declara hasta "
                    f"{MES_LARGO.get(MESES[cubierto_periodo-1], '?') if 1 <= cubierto_periodo <= 7 else 'el año anterior'}, "
                    f"pero el conteo de mensualidades da "
                    f"{max(0, MES_CORTE - cubierto_conteo)} mes(es) de atraso")

        if cfg["estado"] != "activo":
            cobro = "n/a"
        elif cubierto is None:
            cobro = "sin datos"
        elif cubierto > MES_CORTE:
            cobro = "adelantado"      # cubre el mes en curso o mas alla
        elif cubierto == MES_CORTE:
            cobro = "al día"
        elif cubierto == MES_CORTE - 1:
            cobro = "1 mes"
        else:
            cobro = f"{MES_CORTE - cubierto} meses"

        esp_jul = esperado(cfg, "jul")
        fichas.append({
            "cliente": cli, "estado": cfg["estado"], "nota": cfg.get("nota", ""),
            "fee": esp_jul["fee"] if esp_jul else None,
            # tarifa de partida, para saber si un cambio fue subida o bajada
            "fee_inicial": cfg["fee"],
            "con_iva": cfg["iva"],
            "facturado_mes": esp_jul["facturado"] if esp_jul else None,
            "retenido_mes": esp_jul["retenido"] if esp_jul else None,
            "a_cobrar_mes": esp_jul["a_cobrar"] if esp_jul else None,
            "ret_ir": cfg["ret_ir"], "ret_iva": cfg["ret_iva"],
            "cambios": cfg.get("desde") or {},
            "cobrado_total": round(cobrado, 2),
            "honorario_total": round(rep["honorario"], 2),
            "pauta_total": round(rep["pauta"], 2),
            "puntual_total": round(rep["puntual"], 2),
            "por_mes": {mm: {k: round(v, 2) for k, v in por_mes[mm].items()}
                        for mm in MESES},
            # lo que falta por cobrar segun los meses de servicio no cubiertos
            "pendiente": round(max(0, MES_CORTE - (cubierto if cubierto is not None
                                                   else MES_CORTE))
                               * (esperado(cfg, "jul")["a_cobrar"] if cfg["fee"]
                                  else 0), 2) if cfg["estado"] == "activo" else 0,
            "cobro": cobro, "cubierto_hasta": cubierto,
            "cobro_fuente": fuente, "cobro_nota": nota,
            "atraso_meses": atraso_meses,
            "ficha_mes": ficha_mes, "meses_activo": len(activos),
            "primer_mes": activos[0] if activos else "",
            "ultimo_mes": activos[-1] if activos else "",
            "cuadra": cuadra, "desvios": desvios, "dobles": dobles,
            "inferido": cfg.get("inferido", ""), "detalle": detalle,
        })

    # ---- totales de la agencia ----
    tot = {k: round(sum(f[k + "_total"] for f in fichas), 2)
           for k in ("honorario", "pauta", "puntual", "cobrado")}
    ret_mes = round(sum(f["retenido_mes"] or 0 for f in fichas
                        if f["estado"] == "activo"), 2)
    fee_mes = round(sum(f["a_cobrar_mes"] or 0 for f in fichas
                        if f["estado"] == "activo"), 2)

    pendiente = round(sum(f["pendiente"] for f in fichas), 2)
    al_dia = sum(1 for f in fichas if f["cobro"] in ("al día", "adelantado"))
    activas = sum(1 for f in fichas if f["estado"] == "activo")

    out = {"meses": MESES, "clientes": fichas, "totales": tot,
           "honorarios_recurrentes_mes": fee_mes,
           "retenido_mes": ret_mes, "avisos": avisos,
           "pendiente_cobro": pendiente, "cuentas_al_dia": al_dia,
           "cuentas_activas": activas}
    json.dump(out, open("tarifario_2026.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ------------------------------- consola -------------------------------
    print("=" * 100)
    print("HONORARIOS CONTRATADOS vs COBRADO EN BANCO")
    print("=" * 100)
    print(f"{'CLIENTE':<20}{'FEE':>8}{'IVA':>7}{'FACT.':>9}{'RETEN.':>9}"
          f"{'A COBRAR':>10}{'HONOR.':>10}{'PAUTA':>9}{'PUNTUAL':>9}  CUADRA")
    print("-" * 100)
    for f in fichas:
        if f["estado"] in ("puntual", "variable", "sin tarifa"):
            continue
        ok = "sí" if f["cuadra"] else ("REVISAR" if f["cuadra"] is False else "—")
        print(f"{f['cliente']:<20}{f['fee'] or 0:>8,.0f}"
              f"{('15%' if f['con_iva'] else '—'):>7}"
              f"{f['facturado_mes'] or 0:>9,.2f}{f['retenido_mes'] or 0:>9,.2f}"
              f"{f['a_cobrar_mes'] or 0:>10,.2f}{f['honorario_total']:>10,.0f}"
              f"{f['pauta_total']:>9,.0f}{f['puntual_total']:>9,.0f}  {ok}")
    print("-" * 100)
    print(f"{'HONORARIO RECURRENTE / MES (cuentas activas)':<58}{fee_mes:>10,.2f}")
    print(f"{'RETENIDO POR CLIENTES / MES':<58}{ret_mes:>10,.2f}")
    print()
    print(f"{'Cobrado total ene-jul':<32}{tot['cobrado']:>12,.2f}")
    print(f"{'  de eso, honorarios':<32}{tot['honorario']:>12,.2f}"
          f"  ({tot['honorario']/tot['cobrado']*100:.1f}%)")
    print(f"{'  de eso, pauta de clientes':<32}{tot['pauta']:>12,.2f}"
          f"  ({tot['pauta']/tot['cobrado']*100:.1f}%)")
    print(f"{'  de eso, proyectos puntuales':<32}{tot['puntual']:>12,.2f}"
          f"  ({tot['puntual']/tot['cobrado']*100:.1f}%)")

    print()
    print("=" * 100)
    print("CUENTAS QUE NO CUADRAN CON EL TARIFARIO")
    print("=" * 100)
    for f in fichas:
        if f["cuadra"] is not False:
            continue
        print(f"\n{f['cliente']}  (fee {f['fee']:,.0f}"
              f"{' + IVA' if f['con_iva'] else ' cerrados'}"
              f" -> deberían llegar {f['a_cobrar_mes']:,.2f})")
        for d in f["desvios"]:
            print(f"    {d['mes']}: llegó {d['real']:>9,.2f} "
                  f"(esperado {d['esperado']:>9,.2f}, dif {d['dif']:+,.2f})")
    if avisos:
        print("\nSin tarifa asignada:")
        for a in avisos:
            print("   " + a)


if __name__ == "__main__":
    main()
