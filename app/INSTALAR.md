# Instalar la app de captura · 5 minutos

La app vive dentro de tu propia hoja de Google, así que escribe en ella con tu
sesión — sin servidores ni credenciales externas. Sólo tú puedes instalarla
porque requiere tu cuenta.

## Pasos

1. **Abre la hoja** del flujo (la de `2026 CTA PICHINCHA`) y entra a
   **Extensiones → Apps Script**. Se abre el editor con un `Código.gs` vacío.

2. **Pega el código:**
   - Borra el contenido de `Código.gs` y pega el de [`Code.gs`](Code.gs).
   - Menú **+ → HTML**, nómbralo exactamente `Index`, y pega el de
     [`Index.html`](Index.html).
   - Guarda (⌘S).

3. **Pon la clave:** rueda dentada (Configuración del proyecto) →
   **Propiedades del script → Añadir propiedad**:
   - Propiedad: `CLAVE` · Valor: el PIN que quieras (ej. `2026`).
   Sin esta propiedad la app rechaza todo registro.

4. **Publica la app:** botón **Implementar → Nueva implementación → Aplicación
   web**:
   - *Ejecutar como:* **Yo** (tu cuenta — así escribe en la hoja y en tu Drive)
   - *Quién tiene acceso:* **Cualquier usuario con el enlace**
     (el PIN es el candado; quien no lo tenga, no registra nada)
   - Autoriza los permisos cuando lo pida (hoja + Drive).

5. **Copia la URL** que te da (termina en `/exec`). Ábrela en el teléfono y
   **añádela a la pantalla de inicio** — queda como una app más.
   Pásasela a quien deba registrar movimientos, junto con el PIN.

Listo: cada registro añade la fila al libro con su referencia y saldo
corrido, sube las fotos a **Drive → Comprobantes Finanzas → 2026 → 2026-08**
renombradas con fecha y referencia, y deja el enlace en la columna H.
El panel público lo recoge en el siguiente cuarto de hora.

## Opcional: que el panel se actualice al instante

Sin esto, el robot de GitHub pasa cada 15 minutos. Con esto, la app le avisa
en el momento:

1. En GitHub: **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**.
   - *Repository access:* sólo `fvayas/finanzas-agencia`
   - *Permissions:* **Contents → Read and write** (nada más)
2. Copia el token y añádelo en las Propiedades del script (paso 3):
   - Propiedad: `GITHUB_TOKEN` · Valor: el token.

Nada más que hacer: la app lo detecta sola y la confirmación pasará de decir
"en el próximo cuarto de hora" a "se está actualizando ahora mismo".

## Si algo cambia

- **¿Editar la app?** Cambia el código en el editor y **Implementar →
  Administrar implementaciones → ✏️ → Nueva versión**. La URL no cambia.
- **¿Cambiar el PIN?** Edita la propiedad `CLAVE`. Los teléfonos lo
  recuerdan, así que habrá que teclearlo una vez de nuevo.
- **¿Otra pestaña en 2027?** Cambia la constante `HOJA` en `Code.gs`.
