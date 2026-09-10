from db import db
from models import Producto
from openpay_client import consultar_cargo

# Punto UNICO donde se decide si un pedido ya se pago de verdad, para
# que el webhook y la consulta activa de respaldo (routes.py,
# consultar_pedido_publico/mis_pedidos) nunca se desincronicen entre
# si -- ambos llaman a esta misma funcion en vez de tener cada uno su
# propia copia de la logica.


def descontar_inventario(pedido):
    for item in pedido.items or []:
        try:
            producto_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        cantidad = item.get("qty") or 0
        producto = db.session.query(Producto).filter_by(id=producto_id).first()
        if producto:
            producto.stock -= cantidad


def confirmar_pago_si_corresponde(pedido):
    """Vuelve a consultarle a Openpay el estado REAL de un cargo --
    nunca se confia en el payload de un webhook para decidir si algo
    esta pagado, solo en esto. Es un no-op instantaneo para pedidos
    sin cargo de Openpay (ej. transferencia) o que ya se confirmaron
    como pagados, asi que es seguro llamarla en cualquier lugar donde
    se muestre un pedido, no solo desde el webhook."""
    if not pedido.openpay_charge_id or pedido.openpay_estado_pago == "completed":
        return

    resultado = consultar_cargo(pedido.openpay_charge_id)
    if not resultado["ok"]:
        # No se pudo consultar ahorita -- se vuelve a intentar la
        # proxima vez que alguien consulte este pedido (webhook
        # reintentando, o el cliente viendo su pedido de nuevo).
        return

    pedido.openpay_charge_data = resultado["cuerpo"]
    estado_real = resultado["estado"]
    pedido.openpay_estado_pago = estado_real

    # Cualquier valor que no sea explicitamente "completed" o "failed"
    # (incluyendo valores no documentados que Openpay pueda agregar) se
    # trata como "sigue pendiente" -- nunca como pagado. Si el admin ya
    # habia cancelado este pedido antes de que el pago se confirmara,
    # no se descuenta inventario -- ese caso (pago tardio de un pedido
    # ya cancelado) lo debe resolver el admin a mano.
    if estado_real == "completed" and not pedido.stock_descontado and pedido.estado != "Cancelado":
        descontar_inventario(pedido)
        pedido.stock_descontado = True
    elif estado_real == "failed" and pedido.estado == "Pendiente":
        pedido.estado = "Cancelado"

    db.session.commit()
