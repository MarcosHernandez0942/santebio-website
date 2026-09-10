import os
import hmac
from flask import Blueprint, request, jsonify
from db import db
from models import Pedido
from pagos_confirmacion import confirmar_pago_si_corresponde

bp = Blueprint("openpay_webhook", __name__)

# Notificaciones de Openpay: manda un POST con su propio formato JSON
# ({type, event_date, transaction}), no el {accion, token} del resto
# del sitio -- por eso vive en su propio blueprint/ruta en vez de
# colgarse de /api/accion. Ver documents.openpay.mx/docs/webhooks.


def _autorizado():
    usuario_esperado = os.environ.get("OPENPAY_WEBHOOK_USER")
    password_esperado = os.environ.get("OPENPAY_WEBHOOK_PASS")
    # Si no se configuraron credenciales todavia, no se exige Basic
    # Auth (se llenan al registrar la URL del webhook en el Dashboard
    # de Openpay, ya con el sitio desplegado).
    if not usuario_esperado or not password_esperado:
        return True

    auth = request.authorization
    if not auth:
        return False
    return hmac.compare_digest(auth.username or "", usuario_esperado) and hmac.compare_digest(
        auth.password or "", password_esperado
    )


@bp.post("/openpay/webhook")
def openpay_webhook():
    if not _autorizado():
        return jsonify({"error": "No autorizado."}), 401

    body = request.get_json(silent=True) or {}
    tipo = body.get("type")

    if tipo == "verification":
        # El codigo de verificacion se confirma a mano en el Dashboard
        # de Openpay -- basta con que quede en el log del servidor.
        print(f"[openpay webhook] codigo de verificacion: {body.get('verification_code')}")
        return jsonify({"ok": True})

    if tipo in ("charge.succeeded", "charge.refunded"):
        # El payload de Openpay NUNCA se usa para decidir el estado del
        # pedido -- solo sirve para ubicar cual pedido es. El estado
        # real siempre sale de volver a consultarle a la API de
        # Openpay con las credenciales propias (confirmar_pago_si_corresponde),
        # para que nadie pueda marcar un pedido como pagado solo
        # mandando un POST con la forma correcta.
        transaccion = body.get("transaction") or {}
        charge_id = transaccion.get("id")
        order_id = transaccion.get("order_id")

        pedido = None
        if charge_id:
            pedido = db.session.query(Pedido).filter_by(openpay_charge_id=charge_id).first()
        if not pedido and order_id:
            pedido = db.session.query(Pedido).filter_by(folio=order_id).first()

        if pedido:
            confirmar_pago_si_corresponde(pedido)

    # Openpay reintenta el envio hasta recibir 200 OK -- se regresa
    # siempre, incluso si el pedido no se encontro o el tipo no se
    # reconoce, para no generar reintentos innecesarios (la doc pide
    # explicitamente tolerar tipos desconocidos).
    return jsonify({"ok": True})
