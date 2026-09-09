import os
import requests

# El SDK oficial de Python de Openpay (paquete "openpay" en PyPI) no
# instala en Python moderno -- su setup.py usa "use_2to3", una opcion
# de setuptools eliminada hace anos, y ni bajando setuptools se
# arregla porque ademas depende de "distutils" (ya no existe desde
# Python 3.12). Por eso se habla directo con la API REST de Openpay
# (es solo HTTP + autenticacion basica con la llave privada) en vez de
# cargar esa dependencia rota -- es lo mismo que hace el SDK por
# dentro. Ver documents.openpay.mx/docs/introduccion.

SANDBOX_BASE_URL = "https://sandbox-api.openpay.mx/v1"
PRODUCTION_BASE_URL = "https://api.openpay.mx/v1"


def openpay_configurado():
    """True solo si ya se pegaron credenciales reales en .env -- hasta
    entonces "tarjeta" y "tiendas aliadas" se muestran como no
    disponibles en vez de intentar cobrar con una cuenta vacia."""
    return bool(os.environ.get("OPENPAY_MERCHANT_ID")) and bool(os.environ.get("OPENPAY_PRIVATE_KEY"))


def _base_url():
    produccion = os.environ.get("OPENPAY_PRODUCTION", "false").lower() == "true"
    return PRODUCTION_BASE_URL if produccion else SANDBOX_BASE_URL


def _crear_cargo(params):
    merchant_id = os.environ.get("OPENPAY_MERCHANT_ID", "")
    private_key = os.environ.get("OPENPAY_PRIVATE_KEY", "")
    url = f"{_base_url()}/{merchant_id}/charges"

    try:
        respuesta = requests.post(url, json=params, auth=(private_key, ""), timeout=15)
    except requests.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el procesador de pagos. Intenta de nuevo."}

    cuerpo = respuesta.json() if respuesta.content else {}

    if respuesta.status_code >= 400:
        # La API de Openpay regresa {category, error_code, description,
        # http_code, request_id} -- "description" ya viene en espanol.
        mensaje = cuerpo.get("description") or "No se pudo procesar el pago."
        return {"ok": False, "error": mensaje}

    return {"ok": True, "cuerpo": cuerpo}


def crear_cargo_tarjeta(source_id, device_session_id, monto, descripcion, order_id):
    resultado = _crear_cargo({
        "method": "card",
        "source_id": source_id,
        "device_session_id": device_session_id,
        "amount": float(monto),
        "currency": "MXN",
        "description": descripcion,
        "order_id": order_id,
    })
    if not resultado["ok"]:
        return resultado

    cuerpo = resultado["cuerpo"]
    return {"ok": True, "chargeId": cuerpo.get("id"), "estado": cuerpo.get("status")}


def crear_cargo_tienda(monto, descripcion, order_id):
    resultado = _crear_cargo({
        "method": "store",
        "amount": float(monto),
        "currency": "MXN",
        "description": descripcion,
        "order_id": order_id,
    })
    if not resultado["ok"]:
        return resultado

    cuerpo = resultado["cuerpo"]
    metodo_pago = cuerpo.get("payment_method") or {}
    return {
        "ok": True,
        "chargeId": cuerpo.get("id"),
        "estado": cuerpo.get("status"),
        "referencia": metodo_pago.get("reference"),
        "barcodeUrl": metodo_pago.get("barcode_url"),
    }
