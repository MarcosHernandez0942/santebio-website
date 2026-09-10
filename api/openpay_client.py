import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
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

# Vigencia de la referencia de pago en tienda (Paynet) si no se paga.
# Sin mandar esto explicito, Openpay pone un default de 30 dias -- se
# deja como constante facil de ajustar si Marcos/el cliente prefieren
# otro plazo de negocio.
DIAS_VIGENCIA_REFERENCIA_TIENDA = 3

MENSAJE_ERROR_GENERICO = "No pudimos procesar tu pago. Verifica los datos e intenta de nuevo, o elige otro método de pago."


def openpay_configurado():
    """True solo si ya se pegaron credenciales reales en .env -- hasta
    entonces "tarjeta" y "tiendas aliadas" se muestran como no
    disponibles en vez de intentar cobrar con una cuenta vacia."""
    return bool(os.environ.get("OPENPAY_MERCHANT_ID")) and bool(os.environ.get("OPENPAY_PRIVATE_KEY"))


def _base_url():
    produccion = os.environ.get("OPENPAY_PRODUCTION", "false").lower() == "true"
    return PRODUCTION_BASE_URL if produccion else SANDBOX_BASE_URL


def _redondear_monto(monto):
    # Los montos que llegan del carrito se calculan en el navegador
    # (suma de precios) y pueden traer mas de 2 decimales por
    # aritmetica de punto flotante de JavaScript (ej. 269 + 149.99 no
    # da exacto 418.99) -- Openpay ignora silenciosamente los
    # decimales de mas, asi que se redondea explicito aqui con
    # Decimal antes de mandarlo, en vez de confiar en el float tal
    # cual llega.
    return float(Decimal(str(monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _crear_cargo(params, ip_cliente=None):
    merchant_id = os.environ.get("OPENPAY_MERCHANT_ID", "")
    private_key = os.environ.get("OPENPAY_PRIVATE_KEY", "")
    url = f"{_base_url()}/{merchant_id}/charges"
    headers = {"X-Forwarded-For": ip_cliente} if ip_cliente else {}

    try:
        respuesta = requests.post(url, json=params, headers=headers, auth=(private_key, ""), timeout=15)
    except requests.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el procesador de pagos. Intenta de nuevo."}

    cuerpo = respuesta.json() if respuesta.content else {}

    if respuesta.status_code >= 400:
        # El detalle tecnico (category/error_code/description/request_id)
        # nunca debe llegar tal cual al cliente final -- se registra
        # completo en el log del servidor y se regresa un mensaje
        # generico y amigable al llamador.
        print(
            "[openpay] cargo rechazado: "
            f"http_code={respuesta.status_code} category={cuerpo.get('category')} "
            f"error_code={cuerpo.get('error_code')} description={cuerpo.get('description')} "
            f"request_id={cuerpo.get('request_id')}",
            flush=True,
        )
        return {"ok": False, "error": MENSAJE_ERROR_GENERICO}

    return {"ok": True, "cuerpo": cuerpo}


def consultar_cargo(charge_id):
    """Vuelve a preguntarle a Openpay el estado real de un cargo ya
    creado -- nunca hay que confiar en el payload que manda el webhook
    para decidir si un pedido esta pagado, solo en esto. Se usa tanto
    desde el webhook como desde la consulta activa de respaldo (ver
    pagos_confirmacion.py)."""
    merchant_id = os.environ.get("OPENPAY_MERCHANT_ID", "")
    private_key = os.environ.get("OPENPAY_PRIVATE_KEY", "")
    url = f"{_base_url()}/{merchant_id}/charges/{charge_id}"

    try:
        respuesta = requests.get(url, auth=(private_key, ""), timeout=15)
    except requests.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el procesador de pagos."}

    cuerpo = respuesta.json() if respuesta.content else {}

    if respuesta.status_code >= 400:
        print(
            "[openpay] no se pudo consultar el cargo "
            f"{charge_id}: http_code={respuesta.status_code} description={cuerpo.get('description')}",
            flush=True,
        )
        return {"ok": False, "error": MENSAJE_ERROR_GENERICO}

    return {"ok": True, "estado": cuerpo.get("status"), "cuerpo": cuerpo}


def crear_cargo_tarjeta(source_id, device_session_id, monto, descripcion, order_id, ip_cliente=None):
    resultado = _crear_cargo({
        "method": "card",
        "source_id": source_id,
        "device_session_id": device_session_id,
        "amount": _redondear_monto(monto),
        "currency": "MXN",
        "description": descripcion,
        "order_id": order_id,
    }, ip_cliente=ip_cliente)
    if not resultado["ok"]:
        return resultado

    cuerpo = resultado["cuerpo"]
    return {"ok": True, "chargeId": cuerpo.get("id"), "estado": cuerpo.get("status"), "cuerpo": cuerpo}


def crear_cargo_tienda(monto, descripcion, order_id, ip_cliente=None):
    fecha_vencimiento = datetime.now(timezone.utc) + timedelta(days=DIAS_VIGENCIA_REFERENCIA_TIENDA)
    resultado = _crear_cargo({
        "method": "store",
        "amount": _redondear_monto(monto),
        "currency": "MXN",
        "description": descripcion,
        "order_id": order_id,
        "due_date": fecha_vencimiento.isoformat(),
    }, ip_cliente=ip_cliente)
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
        "cuerpo": cuerpo,
    }
