import io
from datetime import datetime
from flask import Blueprint, request, send_file, jsonify
from db import db
from models import Pedido

bp = Blueprint("pdf", __name__)

# Endpoint aparte del patron /api/accion porque regresa un PDF binario,
# no JSON -- mismo criterio que webhook_openpay.py.


MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _formatear_fecha(iso_texto):
    # No se usa strftime("%B") porque el nombre del mes depende del
    # locale del sistema operativo (en este entorno de desarrollo sale
    # en ingles aunque el resto del sitio este en espanol) -- se arma
    # el texto a mano para que sea consistente sin importar el
    # servidor donde corra.
    if not iso_texto:
        return ""
    try:
        fecha = datetime.fromisoformat(iso_texto)
    except ValueError:
        return iso_texto
    return f"{fecha.day} de {MESES_ES[fecha.month - 1]} de {fecha.year}, {fecha.strftime('%H:%M')} hrs"


def _generar_pdf_referencia(pedido):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    VERDE = (0x20 / 255, 0x4F / 255, 0x2B / 255)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    ancho, alto = letter
    y = alto - 30 * mm

    c.setFillColorRGB(*VERDE)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(25 * mm, y, "SanteBio")
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(25 * mm, y, "Referencia de pago por transferencia (SPEI)")
    y -= 12 * mm

    c.setFillColorRGB(0, 0, 0)

    def fila(etiqueta, valor, tamano_valor=13, negritas=True):
        nonlocal y
        c.setFont("Helvetica", 10)
        c.drawString(25 * mm, y, etiqueta)
        y -= 6 * mm
        c.setFont("Helvetica-Bold" if negritas else "Helvetica", tamano_valor)
        c.drawString(25 * mm, y, valor)
        y -= 10 * mm

    fila("Folio de tu pedido", pedido.folio)
    fila("Monto a pagar", f"${float(pedido.total):,.2f} MXN")
    fila("Banco", pedido.openpay_banco or "")
    fila("CLABE interbancaria", pedido.openpay_clabe or "", tamano_valor=15)
    fila("Referencia", pedido.openpay_referencia or "", tamano_valor=15)
    if pedido.openpay_fecha_vencimiento:
        fila("Realiza tu transferencia antes de", _formatear_fecha(pedido.openpay_fecha_vencimiento), negritas=False)

    y -= 4 * mm
    c.setFont("Helvetica", 9)
    texto_instrucciones = [
        "Transfiere el monto exacto desde tu banca en línea o app bancaria a la CLABE de arriba.",
        "No necesitas subir ningún comprobante: la CLABE y la referencia son únicas para tu",
        "pedido, así que en cuanto se reciba tu transferencia lo confirmamos automáticamente y",
        "te notificaremos por correo.",
    ]
    for linea in texto_instrucciones:
        c.drawString(25 * mm, y, linea)
        y -= 5 * mm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@bp.get("/pedido/referencia-pago.pdf")
def referencia_pago_pdf():
    folio = (request.args.get("folio") or "").strip().upper()
    correo = (request.args.get("email") or "").strip().lower()

    if not folio or not correo:
        return jsonify({"error": "Falta el folio o el correo."}), 400

    pedido = db.session.query(Pedido).filter_by(folio=folio).first()
    # Mismo criterio anti-enumeracion que consultar_pedido_publico: un
    # solo mensaje generico si el folio no existe o el correo no
    # coincide.
    if not pedido or (pedido.datos_entrega or {}).get("email", "").strip().lower() != correo:
        return jsonify({"error": "No encontramos un pedido con ese folio y correo."}), 404

    if not pedido.openpay_clabe:
        return jsonify({"error": "Este pedido no tiene una referencia de transferencia generada."}), 404

    pdf_buffer = _generar_pdf_referencia(pedido)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"referencia-pago-{pedido.folio}.pdf",
    )
