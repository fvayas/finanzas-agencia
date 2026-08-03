/**
 * App de captura de movimientos · Finanzas Agencia
 *
 * Vive DENTRO de la hoja de cálculo (Extensiones → Apps Script), así que
 * escribe en ella con la sesión del dueño, sin credenciales aparte.
 *
 * Qué hace con cada registro:
 *   1. Añade la fila al final de "2026 CTA PICHINCHA" con el formato del
 *      libro: fecha, referencia siguiente (01-00XXX), descripción en
 *      mayúsculas, ingreso o egreso, y el saldo corrido calculado.
 *   2. Sube las fotos del comprobante a Drive, en carpetas por mes
 *      (Comprobantes Finanzas/2026/2026-08/), renombradas con fecha,
 *      referencia y descripción.
 *   3. Enlaza el comprobante en la columna H de la misma fila.
 *   4. Si hay token de GitHub guardado, avisa al repositorio para que el
 *      panel se reconstruya al instante (si no, el robot pasa cada 15 min).
 *
 * Propiedades del script (Configuración del proyecto → Propiedades):
 *   CLAVE         PIN de acceso a la app (obligatoria: sin ella no registra)
 *   GITHUB_TOKEN  token fino con Contents RW sobre fvayas/finanzas-agencia
 *                 (opcional: sólo para el refresco instantáneo)
 */

const HOJA = "2026 CTA PICHINCHA";
const HOJA_GID = 535711988;   // id fijo de la pestaña: no cambia ni renombrándola
const CARPETA_RAIZ = "Comprobantes Finanzas";
const REPO = "fvayas/finanzas-agencia";
const ZONA = "America/Guayaquil";

function doGet() {
  return HtmlService.createTemplateFromFile("Index")
    .evaluate()
    .setTitle("Registrar movimiento")
    .addMetaTag("viewport", "width=device-width, initial-scale=1");
}

/** Pestaña del libro + última fila real (referencia con importe). */
function libro_() {
  const hoja = SpreadsheetApp.getActive().getSheets().find(function (h) {
    return h.getSheetId() === HOJA_GID || h.getName().trim() === HOJA;
  });
  if (!hoja) throw new Error('No encuentro la pestaña "' + HOJA + '".');
  const cf = hoja.getRange(1, 3, hoja.getLastRow(), 4).getValues(); // C..F
  let fila = 0, ultimaRef = 0;
  for (let i = cf.length - 1; i >= 0; i--) {
    const m = String(cf[i][0]).match(/01-(\d{5})/);
    const conImporte = String(cf[i][2]) !== "" || String(cf[i][3]) !== "";
    if (m && conImporte) { fila = i + 1; ultimaRef = +m[1]; break; }
  }
  if (!fila) throw new Error("No encuentro el último movimiento con importe.");
  return { hoja: hoja, fila: fila, ultimaRef: ultimaRef,
           saldo: Number(hoja.getRange(fila, 7).getValue()) || 0 };
}

/** Para la cabecera de la app: saldo y última referencia, en vivo. */
function estado() {
  const l = libro_();
  return { ref: "01-" + ("00000" + l.ultimaRef).slice(-5),
           saldo: l.saldo };
}

/** El PIN se compara aquí, nunca viaja al HTML. */
function claveValida_(clave) {
  const guardada = PropertiesService.getScriptProperties().getProperty("CLAVE");
  return guardada && clave === guardada;
}

/**
 * Registra un movimiento. `datos`:
 *   clave, tipo ('ingreso'|'egreso'), fecha 'aaaa-mm-dd',
 *   descripcion, monto (número), fotos: [{b64, nombre, mime}]
 */
function registrar(datos) {
  if (!claveValida_(datos.clave)) throw new Error("Clave incorrecta.");
  if (!(datos.monto > 0)) throw new Error("El monto debe ser mayor que cero.");
  const desc = String(datos.descripcion || "").trim().toUpperCase();
  if (desc.length < 3) throw new Error("Describe el movimiento.");

  // una sola persona escribe a la vez: sin esto, dos capturas simultáneas
  // se llevarían la misma referencia y el mismo saldo
  const cerrojo = LockService.getScriptLock();
  cerrojo.waitLock(20000);
  try {
    const l = libro_();
    const hoja = l.hoja, fila = l.fila, ultimaRef = l.ultimaRef;
    const saldoPrevio = l.saldo;
    const esIngreso = datos.tipo === "ingreso";
    const monto = Math.round(Number(datos.monto) * 100) / 100;
    const saldo = Math.round((saldoPrevio + (esIngreso ? monto : -monto)) * 100) / 100;
    const ref = " 01-" + ("00000" + (ultimaRef + 1)).slice(-5);

    // la fecha se escribe como texto d/m/aaaa, el formato del resto del libro
    const p = String(datos.fecha).split("-");           // aaaa-mm-dd
    const fechaTxt = (+p[2]) + "/" + (+p[1]) + "/" + p[0];

    // ---- comprobantes a Drive, en carpeta del mes ----
    const enlaces = (datos.fotos || []).map(function (f, i) {
      const carpeta = carpetaDelMes_(p[0], p[1]);
      const bytes = Utilities.base64Decode(f.b64);
      const ext = (f.nombre || "").indexOf(".") > -1
        ? f.nombre.slice(f.nombre.lastIndexOf(".")) : ".jpg";
      // la descripción manda en el nombre: así se encuentra la foto
      // buscando lo mismo que se buscaría en la hoja
      const nombre = desc.slice(0, 60) + " · " + p[0] + "-" + p[1] + "-" + p[2] +
        " · " + ref.trim() +
        (datos.fotos.length > 1 ? " (" + (i + 1) + ")" : "") + ext;
      const archivo = carpeta.createFile(
        Utilities.newBlob(bytes, f.mime || "image/jpeg", nombre));
      return archivo.getUrl();
    });

    // ---- la fila, con las columnas del libro (A vacía, B..G) ----
    const destino = fila + 1;
    // la fila nueva hereda el formato de la última real (el " $ " de moneda
    // incluido); sin esto, las celdas de abajo salen como número pelado
    hoja.getRange(fila, 2, 1, 6).copyTo(
      hoja.getRange(destino, 2, 1, 6),
      SpreadsheetApp.CopyPasteType.PASTE_FORMAT, false);
    hoja.getRange(destino, 2, 1, 6).setValues([[
      fechaTxt, ref, desc,
      esIngreso ? monto : "", esIngreso ? "" : monto, saldo,
    ]]);
    // el enlace va en la columna H (la antigua "Tipo", en desuso desde
    // marzo; el panel clasifica por la descripción y no la lee)
    if (enlaces.length) {
      hoja.getRange(destino, 8).setValue(enlaces.join("\n"));
    }

    avisarGitHub_();

    return {
      ref: ref.trim(),
      saldo: saldo,
      fotos: enlaces.length,
      instantaneo: !!PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN"),
    };
  } finally {
    cerrojo.releaseLock();
  }
}

/** Comprobantes Finanzas/2026/2026-08/ — se crea lo que falte. */
function carpetaDelMes_(anio, mes) {
  function hijaONueva(padre, nombre) {
    const it = padre.getFoldersByName(nombre);
    return it.hasNext() ? it.next() : padre.createFolder(nombre);
  }
  let raiz;
  const it = DriveApp.getFoldersByName(CARPETA_RAIZ);
  raiz = it.hasNext() ? it.next() : DriveApp.createFolder(CARPETA_RAIZ);
  return hijaONueva(hijaONueva(raiz, anio), anio + "-" + mes);
}

/** Con token: el panel se reconstruye al momento. Sin él, no pasa nada. */
function avisarGitHub_() {
  const token = PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN");
  if (!token) return;
  try {
    UrlFetchApp.fetch("https://api.github.com/repos/" + REPO + "/dispatches", {
      method: "post",
      contentType: "application/json",
      headers: { Authorization: "Bearer " + token,
                 Accept: "application/vnd.github+json" },
      payload: JSON.stringify({ event_type: "nuevo-movimiento" }),
      muteHttpExceptions: true,
    });
  } catch (e) { /* el cron de 15 min lo recoge igual */ }
}

/**
 * Lee un comprobante con el OCR de Google Drive: sube la imagen convertida
 * a Documento (Drive la OCRea al vuelo), extrae el texto y borra el archivo.
 * Devuelve el monto y la fecha detectados para autollenar el formulario.
 * Gratis, sin llaves externas, dentro de la misma cuenta.
 */
function leerComprobante(foto) {
  var token = ScriptApp.getOAuthToken();
  var frontera = "xxBORDExx";
  var meta = JSON.stringify({
    name: "ocr-temporal", mimeType: "application/vnd.google-apps.document"
  });
  var cuerpo = Utilities.newBlob(
    "--" + frontera + "\r\n" +
    "Content-Type: application/json; charset=UTF-8\r\n\r\n" + meta + "\r\n" +
    "--" + frontera + "\r\nContent-Type: " + (foto.mime || "image/jpeg") +
    "\r\nContent-Transfer-Encoding: base64\r\n\r\n" + foto.b64 + "\r\n" +
    "--" + frontera + "--").getBytes();

  var subida = UrlFetchApp.fetch(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart" +
    "&ocrLanguage=es&fields=id", {
      method: "post",
      contentType: "multipart/related; boundary=" + frontera,
      headers: { Authorization: "Bearer " + token },
      payload: cuerpo, muteHttpExceptions: true });
  if (subida.getResponseCode() >= 300) throw new Error("OCR no disponible.");
  var id = JSON.parse(subida.getContentText()).id;

  try {
    var texto = UrlFetchApp.fetch(
      "https://www.googleapis.com/drive/v3/files/" + id +
      "/export?mimeType=text/plain",
      { headers: { Authorization: "Bearer " + token } }).getContentText();
  } finally {
    UrlFetchApp.fetch("https://www.googleapis.com/drive/v3/files/" + id, {
      method: "delete", headers: { Authorization: "Bearer " + token },
      muteHttpExceptions: true });
  }
  return interpretarComprobante_(texto);
}

/** Del texto del voucher, el monto (con pistas MONTO/VALOR/TOTAL) y la fecha. */
function interpretarComprobante_(texto) {
  var lineas = texto.toUpperCase().split(/\n+/);
  var mejor = null, mejorPuntos = -1;
  var reImporte = /\$?\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2}|\d+[.,]\d{2})\b/g;
  lineas.forEach(function (ln) {
    var pistas = /MONTO|VALOR|TOTAL|DEBITAD|TRANSFERIDO|IMPORTE/.test(ln) ? 2 :
                 /COMISION|SALDO|COSTO/.test(ln) ? -1 : 0;
    var m;
    while ((m = reImporte.exec(ln)) !== null) {
      var v = m[1];
      if (v.indexOf(",") > -1) v = v.replace(/\./g, "").replace(",", ".");
      else if (/^\d{1,3}(\.\d{3})+$/.test(v)) v = v.replace(/\./g, "");
      var num = parseFloat(v);
      if (!(num > 0) || num > 1000000) continue;
      var puntos = pistas * 10 + (num > 1 ? 1 : 0);
      if (puntos > mejorPuntos || (puntos === mejorPuntos && mejor !== null && num > mejor)) {
        mejor = num; mejorPuntos = puntos;
      }
    }
  });
  var f = texto.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](20\d{2})/);
  return {
    monto: mejor,
    fecha: f ? (f[3] + "-" + ("0" + f[2]).slice(-2) + "-" + ("0" + f[1]).slice(-2)) : null,
  };
}
