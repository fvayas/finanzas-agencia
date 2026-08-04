# Finanzas Agencia · 2026

Cuadro de mando financiero de la agencia, construido desde el flujo bancario
de la cuenta Pichincha (Google Sheets, pestaña `2026 CTA PICHINCHA`).

**Panel para compartir:** https://fvayas.github.io/finanzas-agencia/
**Copia de trabajo (artifact):** https://claude.ai/code/artifact/eb3e524d-78d0-4ea4-8f8e-7abbf68040b8

> ⚠️ Este repositorio contiene datos financieros reales de la agencia:
> sueldos, tarifas por cliente y movimientos bancarios.

## Cómo entra un movimiento

**App de captura** (`app/`): formulario móvil que añade la fila al libro con
su referencia y saldo corrido, sube el comprobante a Drive (carpetas por mes,
renombrado con fecha y referencia) y avisa al robot. Instalación en
[`app/INSTALAR.md`](app/INSTALAR.md) — 5 minutos, una sola vez.

**Robot** (`.github/workflows/actualizar-panel.yml`): baja la hoja, corre el
pipeline y publica en Pages. Pasa cada 15 minutos, se puede lanzar a mano
desde Actions, y con el token opcional la app lo dispara al instante.

## Cómo se regenera a mano

La fuente de verdad es el Sheets. Cuando se actualiza, correr en orden:

```bash
python3 categorizar.py     # descarga implícita no: baja el CSV a mano o con curl y clasifica los movimientos
python3 tarifario.py       # cuadra cada cuenta contra su tarifa y retenciones
python3 analisis.py        # P&L, punto de equilibrio, nómina, gastos
python3 flexiahorro.py     # concilia contra el extracto de FlexiAhorro (datos pegados del PDF)
python3 tarjeta.py         # desglosa la tarjeta (datos pegados de los estados de cuenta)
python3 app_resumen.py     # pendientes del mes y por cobrar, para la app de captura
python3 build_dashboard.py # inyecta todo en dashboard_template.html → panel-financiero-2026.html
python3 auditoria.py       # comprueba que ningún movimiento quede fuera de las tablas
```

Para bajar el CSV de la hoja:

```bash
curl -sL "https://docs.google.com/spreadsheets/d/1rGLDMyLP6A83QPQvnIDh_9IMAOESeUrudbvJ_x4cSIk/export?format=csv&gid=535711988" -o 2026.csv
```

## Piezas

| Archivo | Qué hace |
|---|---|
| `categorizar.py` | Motor de clasificación: clientes, nómina, freelance, transferencias propias. Las correcciones confirmadas por Francisco viven en `OVERRIDES`. |
| `tarifario.py` | Tarifas contratadas (`TARIFARIO`), retenciones, estado de cobro (al día / debe N meses) y separación honorario · pauta · puntual. |
| `analisis.py` | P&L mensual, punto de equilibrio, costo por persona con el porqué de cada variación, gastos por categoría. |
| `flexiahorro.py` | Conciliación al centavo contra el extracto del banco (cta. de ahorro). |
| `tarjeta.py` | Los consumos de la Mastercard ····3129, cargo a cargo, desde los estados de cuenta. |
| `app_resumen.py` | Resumen ligero (`app-resumen.json`): sueldos y fijos sin registrar este mes + por cobrar. Lo consulta la app de captura. |
| `build_dashboard.py` | Une todos los JSON dentro de la plantilla y genera el panel final. |
| `dashboard_template.html` | La plantilla: diseño "libro mayor" (negro/rojo/gris/blanco), 12 secciones, desglose en dos niveles al pulsar cualquier cifra, glosario. |
| `auditoria.py` | Cobertura: verifica que los 500+ movimientos aparezcan en alguna tabla. |

## Decisiones del modelo (no se deducen de los datos)

- La **pauta** es dinero de paso: se resta de ingresos y de gastos; sólo la no
  recuperada cuenta como costo.
- Karen, Marissa y Josué son **plantilla fija**; la pasantía es una plaza que
  rota (Karla → Nicole Cuesta, ago-2026).
- Speedy devenga desde **mayo** aunque su primer giro fue en junio.
- "Velas Tungurahua" = **Velsana**. "Gym" era un error: eran pagos de Absolute.
- El estado de cobro se lee del **periodo declarado** en la descripción de
  cada giro ("del 18 de junio al 18 de julio").
- Healthy Girl baja a **600 + IVA desde julio 2026**.
