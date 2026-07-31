#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Categorizador del flujo bancario 2026 - Cta. Pichincha
Lee el CSV publicado de la pestana "2026 CTA PICHINCHA" y clasifica
los 496 movimientos desde cero en un esquema de 3 niveles:

  NIVEL 1  naturaleza : OPERATIVO | NO OPERATIVO
  NIVEL 2  grupo      : agrupacion para P&L y punto de equilibrio
  NIVEL 3  categoria  : detalle (cliente, persona, concepto)

Salida: movimientos_2026.csv  +  resumen_2026.json
"""
import csv, json, re, unicodedata
from collections import defaultdict, OrderedDict

SRC = "2026.csv"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul",
         "ago", "sep", "oct", "nov", "dic"]


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------
def limpia(s):
    """Normaliza texto: mayusculas, sin tildes, sin dobles espacios."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper()).strip()


def monto(s):
    """' $ 1.234,56 ' -> 1234.56 ; ' $ -362,00 ' -> -362.0 ; vacio -> 0.0

    El signo se conserva: la hoja tiene importes negativos dentro de la
    columna Ingreso (devoluciones) que en realidad son salidas de dinero.
    """
    s = (s or "").replace("$", "").replace(" ", "").strip()
    if not s:
        return 0.0
    neg = s.startswith("-")
    s = s.lstrip("-").replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def parse_fecha(s):
    """d/m/aaaa -> (aaaa, m, d). Corrige el typo 2206 -> 2026."""
    p = (s or "").strip().split("/")
    if len(p) != 3:
        return None
    try:
        d, m, a = int(p[0]), int(p[1]), int(p[2])
    except ValueError:
        return None
    if a == 2206:          # typo detectado en 19 filas de abril
        a = 2026
    return (a, m, d)


# --------------------------------------------------------------------------
# diccionarios de reconocimiento
# --------------------------------------------------------------------------

# Clientes de la agencia. clave = patron regex ; valor = nombre canonico
CLIENTES = OrderedDict([
    (r"HEALTHY\s*GIRL|HELATHY\s*GIRL|MODELO HEALTHY|HELATHY|HEALTHY",
                                                  "Healthy Girl"),
    (r"FIAMMINGO",                                "Fiammingo"),
    (r"PLADECO",                                  "Pladeco"),
    (r"VELSANA|VELAS TUNGURAHUA",                 "Velsana"),
    (r"CIGARRA",                                  "Cigarra"),
    (r"UNINOVA",                                  "Uninova"),
    (r"PLASTICAUCHO",                             "Plasticaucho"),
    (r"TARTELIER",                                "Tartelier"),
    (r"SAMARI",                                   "Samari"),
    (r"PROVITA",                                  "Provita"),
    (r"FLOTA IMBABURA",                           "Flota Imbabura"),
    (r"CONFIA",                                   "Confia"),
    (r"CHIFLIDO|CHILIDO",                         "Chiflido"),
    (r"FRIENDS? GUIDES|FREINDS GUIDES|FRENDS GUIDES|FRIEND GUIDES|\bFRIENDS\b",
                                                  "Friends Guides"),
    (r"\bNONO\b",                                 "Nono"),
    (r"LA TARTUCA|TARTUCA",                       "La Tartuca"),
    (r"VICTOR HUGO",                              "Victor Hugo (evento)"),
    (r"CASA DEL VERDE|CASA VERDE",                "Casa del Verde"),
    (r"ONCO AMBATO",                              "Onco Ambato"),
    (r"ABSOLUTE",                                 "Absolute"),
    (r"NANE",                                     "Nane Vestidos"),
    (r"SPEEDY",                                   "Speedy"),
    (r"MM\s*WINGS|MMWINGS|MM WINNGS",             "MM Wings"),
    (r"EL MOTOR|PAGO MOTOR",                      "El Motor"),
    (r"PASTEUR",                                  "Pasteur"),
    (r"\bAPC\b",                                  "APC"),
    (r"DOG SPA",                                  "Dog Spa"),
    (r"NICRIS",                                   "Nicris"),
    (r"TIENDA ELECTRO",                           "Tienda Electro"),
    # "Gym" existia por un error de la hoja: esos pagos eran de Absolute.
    # Corregido en origen el 31/07/2026.
])

# Nomina. clave = patron ; valor = (nombre, tipo_contrato)
#   FIJO    -> plantilla estable, cuenta como costo fijo
#   SOCIO   -> sueldo de los duenos
#   PASANTE -> pasantia, rota cada pocos meses, costo fijo pero de otro orden
#   VAR     -> pago puntual / por proyecto
NOMINA = OrderedDict([
    (r"ANA\s*PAULA|\bA\.?P\.?\b",                 ("Ana Paula", "SOCIO")),
    (r"FRANCISCO\s*VAYAS|SUELDO FRANCISCO",       ("Francisco Vayas", "SOCIO")),
    (r"ALEJANDRA\s*APONTE|ALE APONTE|SUELDO ALE\b",("Alejandra Aponte", "FIJO")),
    (r"ALEJANDR?O\s*VACA|ALEJANDO VACA|ALEJANDRO|ALEJO",
                                                  ("Alejandro Vaca", "FIJO")),
    (r"ESTEFI|ESTEFITA",                          ("Estefi Jacome", "FIJO")),
    (r"STALIN",                                   ("Stalin Bonilla", "FIJO")),
    (r"DANNA",                                    ("Danna Cardenas", "FIJO")),
    (r"MIGUEL\s*MOLINA|SUELDO MIGUEL",            ("Miguel Molina", "FIJO")),
    (r"DANIELA\s*CORDOVA|DANIE\s*CORDOVA",        ("Daniela Cordova", "FIJO")),
    (r"JOSUE",                                    ("Josue Lara", "FIJO")),
    (r"MARISSA",                                  ("Marissa Alban", "FIJO")),
    (r"KAREN\s*PINOS|KAREN",                      ("Karen Pinos", "FIJO")),
    (r"MIKAELA\s*VARGAS",                         ("Mikaela Vargas", "VAR")),
    # pasantias: rotan cada pocos meses. Karla salio, Nicole entra en agosto.
    (r"KARLA|KARLITA",                            ("Karla Jacome", "PASANTE")),
    (r"NICOLE\s*CUESTA|NICOLE",                   ("Nicole Cuesta", "PASANTE")),
])

# Freelance / produccion externa
FREELANCE = OrderedDict([
    (r"NICOLAS",                  "Nicolas Encalada (foto/video)"),
    (r"JUAN\s*?PABLO|JUANPABLO",  "Juan Pablo Nieto (produccion)"),
    (r"PRIS\s*RODRIGUEZ",         "Pris Rodriguez (produccion)"),
    (r"DIEGO\s*RODRIGUEZ|JUANDI", "Diego Rodriguez / Juandi (locacion)"),
    (r"ISMAEL\s*MAYORGA",         "Ismael Mayorga (video)"),
    (r"SOFIA\s*GARZON",           "Sofia Garzon (flores/deco)"),
    # OJO: 'PAULITA' con límites de palabra. Un patrón 'PAULA' capturaría
    # los sueldos de Ana Paula, porque freelance se evalúa antes que nómina.
    (r"AMELIA\s*PADILLA|MODELO|\bPAULITA\b", "Modelos"),
    (r"ACTOR",                    "Actores"),
    (r"VIDEOGRAFO",               "Videografo"),
    (r"\bPLANTAS\b|\bFLORES\b",   "Ambientacion / props"),
])


# --------------------------------------------------------------------------
# Correcciones confirmadas por Francisco sobre filas que la hoja dejo ambiguas.
# Se aplican despues de clasificar. Anadir aqui cualquier atribucion futura.
#   (fecha, fragmento de la descripcion, grupo, categoria, detalle)
# --------------------------------------------------------------------------
OVERRIDES = [
    # la fila no lleva nombre; confirmado que son horas extras de Alejandro Vaca.
    # La hoja ya se corrigio en origen, se deja por si vuelve a aparecer asi.
    ("18/05/2026", "PAGO HORAS EXTRAS DE FERIADO",
     "Nomina variable", "Horas extras", "Alejandro Vaca"),
    # "Alpes" no es un cliente: es una marca de Pladeco. El giro es pauta,
    # no honorario de agencia, asi que va al bucket de pauta de Pladeco.
    ("24/02/2026", "PAUTA ALPES",
     "Ingresos - Pauta", "Pauta reembolsada", "Pladeco"),
    # Francisco no reconoce este cobro. La hoja ya lo marca como
    # "NO IDENTIFICADO"; aqui solo se le pone una etiqueta legible.
    ("12/03/2026", "NO IDENTIFICADO",
     "Ingresos - Sin identificar", "REVISAR", "Cobro de marzo sin identificar"),
]


def busca(patrones, texto):
    for pat, val in patrones.items():
        if re.search(pat, texto):
            return val
    return None


# --------------------------------------------------------------------------
# motor de clasificacion
# --------------------------------------------------------------------------
def clasifica(desc, ingreso, egreso):
    """Devuelve (naturaleza, grupo, categoria, detalle)."""
    d = limpia(desc)
    es_ing = ingreso > 0

    # ---------- 0. saldo inicial ----------
    if "SALDO INICIAL" in d:
        return ("NO OPERATIVO", "Saldo Inicial", "Saldo Inicial", "")

    # ---------- 1. movimientos entre cuentas propias ----------
    # FlexiAhorro y Fideval son cuentas de ahorro de la propia agencia.
    # Entran y salen de Pichincha pero NO son ingreso ni gasto real.
    # Son dos fondos distintos y conviene verlos separados: FlexiAhorro es la
    # cuenta operativa de la que se repone a diario; Fideval es la de largo
    # plazo. "Ahorro programado" y "ahorro flexible" son debitos de FlexiAhorro.
    if re.search(r"FLEXI\s*AHORRO|FLEXIAHORRO|FELXIAHORRO|FLEXIAHORO|"
                 r"FLEXIAHRRO|FLEXIAHRO|AHORRO PROGRAMADO|AHORRO FLEXIBLE|"
                 r"FIDEVAL", d):
        fondo = "Fideval" if "FIDEVAL" in d else "FlexiAhorro"
        sentido = f"Entrada desde {fondo}" if es_ing else f"Salida a {fondo}"
        return ("NO OPERATIVO", "Movimiento entre cuentas propias",
                sentido, desc.strip())

    if re.search(r"FALLO BANCO REVERSO|REVERSO DE", d):
        return ("NO OPERATIVO", "Movimiento entre cuentas propias",
                "Reverso bancario", desc.strip())

    # ---------- 2. utilidades / retiros de socios ----------
    if "UTILIDAD" in d:
        quien = busca(NOMINA, d)
        return ("NO OPERATIVO", "Retiro de socios", "Utilidades",
                quien[0] if quien else "")

    # =========================  INGRESOS  =========================
    if es_ing:
        # interes bancario
        if "INTERES BANCARIO" in d:
            return ("OPERATIVO", "Otros ingresos", "Interes bancario", "")

        # subarriendo de oficina: Friends Guides y Chiki comparten el espacio.
        # No son cuentas de la agencia, es alquiler de un puesto de trabajo.
        if re.search(r"ARRIENDO|ARREINDO", d):
            quien = ("Chiki" if re.search(r"CHIKI|CHIQUI", d)
                     else busca(CLIENTES, d) or "")
            return ("OPERATIVO", "Otros ingresos", "Subarriendo oficina", quien)

        cli = busca(CLIENTES, d)

        # recuperacion de pauta facturada al cliente
        if re.search(r"PAUTA", d):
            return ("OPERATIVO", "Ingresos - Pauta", "Pauta reembolsada",
                    cli or "Sin identificar")

        # produccion audiovisual puntual (fuera de fee)
        if re.search(r"PRODUCCION|VIDEO|PODCAST|WEB\b|FOTOS|BRANDING|"
                     r"FIESTA|EVENTO|ENTRADAS", d):
            return ("OPERATIVO", "Ingresos - Produccion", "Proyecto puntual",
                    cli or "Sin identificar")

        if cli:
            return ("OPERATIVO", "Ingresos - Fee mensual", cli, desc.strip())

        # sobrantes menores (venta interna, devoluciones)
        if re.search(r"SANDUCHE|DEVOLUCION|ABONO", d):
            return ("OPERATIVO", "Otros ingresos", "Menores", desc.strip())

        return ("OPERATIVO", "Ingresos - Sin identificar", "REVISAR",
                desc.strip())

    # =========================  EGRESOS  ==========================

    # ---------- tarjeta de credito ----------
    # OJO: es un pago de deuda, el gasto real esta en el estado de cuenta.
    if re.search(r"TARJETA", d):
        return ("OPERATIVO", "Tarjeta de credito",
                "Pago tarjeta (sin desglose)", desc.strip())

    # ---------- impuestos ----------
    # va antes que devoluciones: "devolucion impuestos" es carga fiscal,
    # no una devolucion a cliente.
    if "IMPUESTO" in d:
        return ("OPERATIVO", "Impuestos y legal", "Impuestos", desc.strip())

    # ---------- devoluciones a clientes ----------
    if "DEVOLUCION" in d:
        return ("OPERATIVO", "Devoluciones", "Devolucion a cliente",
                desc.strip())

    # ---------- reembolso de pauta ----------
    if re.search(r"REEMBOLSO PAUTA|PAUTA", d):
        return ("OPERATIVO", "Pauta", "Pauta pagada", desc.strip())

    # ---------- freelance / produccion ----------
    fl = busca(FREELANCE, d)
    if fl:
        cli = busca(CLIENTES, d)
        return ("OPERATIVO", "Freelance y produccion", fl, cli or "")

    # ---------- nomina ----------
    persona = busca(NOMINA, d)
    if persona and re.search(r"SUELDO|QUINCENA|HORA|NOMINA|PAGO A |PAGO FINAL|"
                             r"AUMENTO|DESCUENTO", d):
        nombre, tipo = persona
        # horas extras y feriados = costo variable aunque sea plantilla fija
        if re.search(r"HORA[S]? EXTRA|FERIADO", d):
            return ("OPERATIVO", "Nomina variable", "Horas extras", nombre)
        grupo = {"SOCIO":   "Nomina socios",
                 "FIJO":    "Nomina fija",
                 "PASANTE": "Pasantias",
                 "VAR":     "Nomina variable"}[tipo]
        return ("OPERATIVO", grupo, nombre, desc.strip())

    # horas extras sin nombre asociado
    if re.search(r"HORA[S]? EXTRA|FERIADO", d):
        return ("OPERATIVO", "Nomina variable", "Horas extras", desc.strip())

    # ---------- movilizacion ----------
    if re.search(r"TAXI|TADIS|UBER|MOVILIZ|PARQUEO|VIATICO", d):
        p = busca(NOMINA, d)
        return ("OPERATIVO", "Movilizacion", "Taxis / parqueo / viaticos",
                p[0] if p else "")

    # ---------- estructura fisica ----------
    if re.search(r"ARRIENDO|ARREINDO|CONDOMINIO|ALICUOTA", d):
        return ("OPERATIVO", "Estructura", "Arriendo, condominio y alicuotas",
                desc.strip())
    if re.search(r"\bAGUA\b|LUZ|ELECTRIC|SERVICIOS BASICOS", d):
        return ("OPERATIVO", "Estructura", "Servicios basicos", desc.strip())
    if "INTERNET" in d:
        return ("OPERATIVO", "Estructura", "Internet", desc.strip())
    if "LIMPIEZA" in d:
        return ("OPERATIVO", "Estructura", "Limpieza", desc.strip())

    # ---------- software y herramientas ----------
    if re.search(r"SISTEMA CONTABLE|SISTEMA FACTURACION|FACTURACION|"
                 r"CHAT\s*GPT|CHAT\s*FUEL|SOFTWARE|SUSCRIPCION", d):
        return ("OPERATIVO", "Software y herramientas", "Suscripciones",
                desc.strip())

    # ---------- equipos ----------
    if re.search(r"COMPUTADOR|EQUIPO|RESETEO|REVISION COMPUTADOR|"
                 r"ELECTRODOMESTICO|CAMARA|LENTE|SONNY|SONY", d):
        return ("OPERATIVO", "Equipos", "Equipos y mantenimiento",
                desc.strip())

    # ---------- oficina y bienestar del equipo ----------
    if re.search(r"BOTELLON|CAFE|AZUCAR|SANDUCHE|CERVEZA|ALMUERZO|"
                 r"REFRIGERIO|SUPERMAXI|COMPRAS OFI|ACAI|CUMPLEA", d):
        return ("OPERATIVO", "Oficina y bienestar", "Refrigerios y suministros",
                desc.strip())

    # ---------- uniformes / branding ----------
    if re.search(r"UNIFORME|CAPUCHA|BRANDING", d):
        return ("OPERATIVO", "Marketing propio", "Uniformes y branding",
                desc.strip())

    # ---------- gasto directo atribuible a un cliente ----------
    cli = busca(CLIENTES, d)
    if cli:
        return ("OPERATIVO", "Freelance y produccion", "Gasto de proyecto", cli)

    return ("OPERATIVO", "Egresos - Sin identificar", "REVISAR", desc.strip())


# --------------------------------------------------------------------------
# proceso
# --------------------------------------------------------------------------
def main():
    filas = list(csv.reader(open(SRC, encoding="utf-8")))
    out = []
    typo_fecha = 0

    for r in filas[4:]:
        if len(r) < 7:
            continue
        f = parse_fecha(r[1])
        if not f:
            continue
        ing, egr = monto(r[4]), monto(r[5])
        if ing == 0 and egr == 0:
            continue                      # filas vacias de relleno
        # un "ingreso" negativo es en realidad una salida de dinero
        if ing < 0:
            egr += -ing
            ing = 0.0
        if egr < 0:
            ing += -egr
            egr = 0.0
        if (r[1] or "").strip().endswith("2206"):
            typo_fecha += 1

        nat, grupo, cat, det = clasifica(r[3], ing, egr)
        anio, mes, dia = f
        fecha_txt = f"{dia:02d}/{mes:02d}/{anio}"
        for f_ov, frag, g_ov, c_ov, d_ov in OVERRIDES:
            if fecha_txt == f_ov and frag in limpia(r[3]):
                grupo, cat, det = g_ov, c_ov, d_ov
                break
        out.append({
            "fecha":      fecha_txt,
            "anio":       anio,
            "mes_num":    mes,
            "mes":        MESES[mes - 1],
            "referencia": (r[2] or "").strip(),
            "descripcion": (r[3] or "").strip(),
            "ingreso":    round(ing, 2),
            "egreso":     round(egr, 2),
            "neto":       round(ing - egr, 2),
            "naturaleza": nat,
            "grupo":      grupo,
            "categoria":  cat,
            "detalle":    det,
            "tipo_original": (r[7] or "").strip(),
        })

    out.sort(key=lambda x: (x["anio"], x["mes_num"], int(x["fecha"][:2])))

    with open("movimientos_2026.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    # ---------------- resumen ----------------
    meses_pres = sorted({m["mes_num"] for m in out})
    piv = defaultdict(lambda: defaultdict(float))
    for m in out:
        signo = m["ingreso"] - m["egreso"]
        piv[(m["naturaleza"], m["grupo"])][m["mes_num"]] += signo

    print(f"Movimientos procesados : {len(out)}")
    print(f"Typos de fecha 2206 corregidos : {typo_fecha}")
    print(f"Meses con datos : {[MESES[i-1] for i in meses_pres]}")
    print()
    hdr = "  ".join(f"{MESES[i-1]:>10}" for i in meses_pres)
    print(f"{'GRUPO':<38}{hdr}{'TOTAL':>12}")
    print("-" * (38 + 12 * len(meses_pres) + 12))
    for nat in ["OPERATIVO", "NO OPERATIVO"]:
        print(f"\n[{nat}]")
        for (n, g), vals in sorted(piv.items(), key=lambda x: -abs(sum(x[1].values()))):
            if n != nat:
                continue
            fila = "  ".join(f"{vals.get(i,0):>10,.0f}" for i in meses_pres)
            print(f"{g:<38}{fila}{sum(vals.values()):>12,.0f}")

    sin_id = [m for m in out if "Sin identificar" in m["grupo"]]
    print(f"\nSin identificar: {len(sin_id)} movimientos "
          f"(${sum(abs(m['neto']) for m in sin_id):,.2f})")
    for m in sin_id:
        print(f"   {m['fecha']}  {m['neto']:>10,.2f}  {m['descripcion'][:60]}")

    json.dump(out, open("movimientos_2026.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
