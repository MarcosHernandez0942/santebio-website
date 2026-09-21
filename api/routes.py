import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from flask import Blueprint, request, jsonify
from auth import firmar_token, verificar_token
from db import db
from email_utils import (
    enviar_correo_restablecer,
    enviar_correo_confirmacion_pedido,
    enviar_correo_nuevo_pedido_admin,
    enviar_correo_cambio_estado_pedido,
)
from models import (
    Usuario, Admin, Pedido, Direccion, Tarjeta, TokenRestablecer, Opinion, Producto, AvisoStock,
    PlanSuscripcion, Suscripcion,
    expandir_items_a_individuales, calcular_stock_paquete, COMPOSICION_PAQUETES,
)
from openpay_client import openpay_configurado, crear_cargo_tarjeta, crear_cargo_tienda, crear_cargo_spei
from pagos_confirmacion import confirmar_pago_si_corresponde

bp = Blueprint("accion", __name__)

ESTADOS_PEDIDO = {"Pendiente", "Aceptado", "Enviado", "Entregado", "Cancelado"}

ACCIONES_PUBLICAS = {
    "registro_usuario", "login_usuario", "login_admin", "crear_pedido",
    "solicitar_cambio_password", "confirmar_cambio_password",
    "listar_opiniones_publicas", "calificaciones_por_producto",
    "consultar_pedido_publico", "listar_productos_publico",
    "listar_planes_suscripcion_publico",
}
# "nueva_opinion" YA NO es publica a proposito: solo clientes con
# sesion iniciada pueden opinar (pedido de Marcos, "para que se filtre
# aun mas y solo clientes puedan opinar").

# Sin 0/O/1/I ni vocales que formen palabras raras por accidente -- un
# folio se lee/escribe a mano, asi que evita caracteres que se
# confunden entre si.
_ALFABETO_FOLIO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_folio():
    sufijo = "".join(secrets.choice(_ALFABETO_FOLIO) for _ in range(6))
    return f"SB-{sufijo}"


@bp.post("/accion")
def accion():
    body = request.get_json(silent=True) or {}
    tipo_accion = body.get("accion")
    token = body.get("token")

    if not tipo_accion:
        return jsonify({"error": "Falta el parámetro accion."}), 400

    datos_token = verificar_token(token) if token else None
    if tipo_accion not in ACCIONES_PUBLICAS and not datos_token:
        return jsonify({"error": "No autorizado."}), 401

    try:
        if tipo_accion == "registro_usuario":
            return registro_usuario(body)
        if tipo_accion == "login_usuario":
            return login_usuario(body)
        if tipo_accion == "login_admin":
            return login_admin(body)
        if tipo_accion == "crear_pedido":
            return crear_pedido(body, datos_token)
        if tipo_accion == "consultar_pedido_publico":
            return consultar_pedido_publico(body)
        if tipo_accion == "listar_kpis_admin":
            return listar_kpis_admin(datos_token)
        if tipo_accion == "listar_direcciones":
            return listar_direcciones(datos_token)
        if tipo_accion == "guardar_direccion":
            return guardar_direccion(body, datos_token)
        if tipo_accion == "eliminar_direccion":
            return eliminar_direccion(body, datos_token)
        if tipo_accion == "actualizar_perfil":
            return actualizar_perfil(body, datos_token)
        if tipo_accion == "solicitar_cambio_password":
            return solicitar_cambio_password(body, datos_token)
        if tipo_accion == "confirmar_cambio_password":
            return confirmar_cambio_password(body)
        if tipo_accion == "mis_pedidos":
            return mis_pedidos(datos_token)
        if tipo_accion == "listar_tarjetas":
            return listar_tarjetas(datos_token)
        if tipo_accion == "guardar_tarjeta":
            return guardar_tarjeta(body, datos_token)
        if tipo_accion == "eliminar_tarjeta":
            return eliminar_tarjeta(body, datos_token)
        if tipo_accion == "listar_pedidos_admin":
            return listar_pedidos_admin(datos_token)
        if tipo_accion == "actualizar_estado_pedido":
            return actualizar_estado_pedido(body, datos_token)
        if tipo_accion == "obtener_comprobante_pedido":
            return obtener_comprobante_pedido(body, datos_token)
        if tipo_accion == "listar_productos_publico":
            return listar_productos_publico()
        if tipo_accion == "listar_productos_admin":
            return listar_productos_admin(datos_token)
        if tipo_accion == "crear_producto":
            return crear_producto(body, datos_token)
        if tipo_accion == "actualizar_producto":
            return actualizar_producto(body, datos_token)
        if tipo_accion == "listar_avisos_stock":
            return listar_avisos_stock(datos_token)
        if tipo_accion == "marcar_avisos_stock_revisados":
            return marcar_avisos_stock_revisados(datos_token)
        if tipo_accion == "listar_planes_suscripcion_publico":
            return listar_planes_suscripcion_publico()
        if tipo_accion == "listar_planes_suscripcion_admin":
            return listar_planes_suscripcion_admin(datos_token)
        if tipo_accion == "crear_plan_suscripcion":
            return crear_plan_suscripcion(body, datos_token)
        if tipo_accion == "actualizar_plan_suscripcion":
            return actualizar_plan_suscripcion(body, datos_token)
        if tipo_accion == "listar_suscripciones_admin":
            return listar_suscripciones_admin(datos_token)
        if tipo_accion == "crear_suscripcion_admin":
            return crear_suscripcion_admin(body, datos_token)
        if tipo_accion == "actualizar_suscripcion_admin":
            return actualizar_suscripcion_admin(body, datos_token)
        if tipo_accion == "registrar_entrega_suscripcion":
            return registrar_entrega_suscripcion(body, datos_token)
        if tipo_accion == "nueva_opinion":
            return nueva_opinion(body, datos_token)
        if tipo_accion == "listar_opiniones_publicas":
            return listar_opiniones_publicas()
        if tipo_accion == "calificaciones_por_producto":
            return calificaciones_por_producto()
        if tipo_accion == "listar_opiniones_admin":
            return listar_opiniones_admin(datos_token)
        if tipo_accion == "aprobar_opinion":
            return cambiar_estado_opinion(body, datos_token, desde="pendiente", hasta="aprobado")
        if tipo_accion == "ocultar_opinion":
            return cambiar_estado_opinion(body, datos_token, desde="aprobado", hasta="oculto")
        if tipo_accion == "mostrar_opinion":
            return cambiar_estado_opinion(body, datos_token, desde="oculto", hasta="aprobado")
        if tipo_accion == "rechazar_opinion":
            return eliminar_opinion(body, datos_token, desde="pendiente")
        if tipo_accion == "eliminar_opinion":
            return eliminar_opinion(body, datos_token, desde="oculto")
        return jsonify({"error": "Acción no reconocida."}), 400
    except Exception as error:  # noqa: BLE001
        import traceback
        print(f"[accion:{tipo_accion}] " + traceback.format_exc(), flush=True)
        return jsonify({"error": "Error interno del servidor."}), 500


def exigir_tipo(datos_token, tipo):
    return bool(datos_token) and datos_token.get("tipo") == tipo


def registro_usuario(body):
    nombre = body.get("nombre")
    correo = body.get("correo")
    telefono = body.get("telefono") or ""
    password = body.get("password")

    if not nombre or not correo or not password:
        return jsonify({"error": "Faltan datos obligatorios (nombre, correo, contraseña)."}), 400

    existente = db.session.query(Usuario).filter_by(correo=correo).first()
    if existente:
        return jsonify({"ok": False, "error": "Ya existe una cuenta con ese correo."})

    hash_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    usuario = Usuario(nombre=nombre, correo=correo, telefono=telefono, password_hash=hash_password)
    db.session.add(usuario)
    db.session.commit()

    token = firmar_token({"usuarioId": usuario.id, "correo": usuario.correo, "tipo": "usuario"})
    return jsonify({"ok": True, "token": token, "usuario": usuario.to_dict()})


def login_usuario(body):
    correo = body.get("correo")
    password = body.get("password") or ""

    usuario = db.session.query(Usuario).filter_by(correo=correo).first()
    if not usuario or not bcrypt.checkpw(password.encode("utf-8"), usuario.password_hash.encode("utf-8")):
        return jsonify({"ok": False, "error": "Correo o contraseña incorrectos."})

    token = firmar_token({"usuarioId": usuario.id, "correo": usuario.correo, "tipo": "usuario"})
    return jsonify({"ok": True, "token": token, "usuario": usuario.to_dict()})


def login_admin(body):
    usuario_valor = body.get("usuario")
    password = body.get("password") or ""

    admin = db.session.query(Admin).filter_by(usuario=usuario_valor).first()
    if not admin or not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
        return jsonify({"ok": False})

    token = firmar_token({"usuario": usuario_valor, "tipo": "admin"})
    return jsonify({"ok": True, "token": token})


MAX_COMPROBANTE_BASE64 = 7_000_000  # ~5 MB de archivo real antes de base64


def crear_pedido(body, datos_token):
    items = body.get("items")
    total = body.get("total")
    metodo_pago = body.get("metodoPago") or ""
    datos_entrega = body.get("datosEntrega")
    comprobante = body.get("comprobante")
    ip_cliente = request.remote_addr

    if not items or total is None or not datos_entrega:
        return jsonify({"error": "Pedido inválido."}), 400

    comprobante_nombre = comprobante_tipo = comprobante_datos = None
    if comprobante:
        comprobante_datos = comprobante.get("datosBase64")
        if comprobante_datos and len(comprobante_datos) > MAX_COMPROBANTE_BASE64:
            return jsonify({"error": "El comprobante es demasiado grande (máximo 5 MB)."}), 400
        comprobante_nombre = comprobante.get("nombre")
        comprobante_tipo = comprobante.get("tipo")

    # El folio se genera ANTES de intentar cualquier cargo de Openpay
    # porque se manda como "order_id" del cargo -- asi se puede
    # relacionar el cargo con el pedido incluso si algo falla a medias
    # (el folio simplemente se descarta si el cargo no procede, ver
    # abajo).
    folio = generar_folio()
    while db.session.query(Pedido).filter_by(folio=folio).first():
        folio = generar_folio()

    descripcion_cargo = f"Pedido {folio} - SanteBio Cápsulas de Nopal"
    openpay_charge_id = openpay_referencia = openpay_barcode_url = None
    openpay_charge_data = None
    openpay_estado_pago = None
    openpay_clabe = openpay_banco = openpay_fecha_vencimiento = None
    # True solo si ESTE pedido en particular se cobra a traves de
    # Openpay -- no se puede usar el nombre del metodo directo porque
    # "transferencia" tiene dos comportamientos segun si ya hay
    # credenciales configuradas (ver mas abajo).
    usa_openpay_para_este_metodo = False

    if metodo_pago == "tarjeta":
        if not openpay_configurado():
            return jsonify({"error": "Los pagos con tarjeta aún no están disponibles. Intenta con transferencia o en tiendas aliadas."}), 400
        source_id = body.get("openpayTokenId")
        device_session_id = body.get("openpayDeviceSessionId")
        if not source_id or not device_session_id:
            return jsonify({"error": "No se pudo leer la tarjeta. Intenta de nuevo."}), 400
        resultado_cargo = crear_cargo_tarjeta(source_id, device_session_id, total, descripcion_cargo, folio, ip_cliente=ip_cliente)
        if not resultado_cargo["ok"]:
            return jsonify({"error": resultado_cargo["error"]}), 400
        openpay_charge_id = resultado_cargo["chargeId"]
        openpay_charge_data = resultado_cargo["cuerpo"]
        openpay_estado_pago = resultado_cargo["estado"]
        usa_openpay_para_este_metodo = True
    elif metodo_pago == "tiendas-aliadas":
        if not openpay_configurado():
            return jsonify({"error": "El pago en tiendas aliadas aún no está disponible. Intenta con transferencia o tarjeta."}), 400
        resultado_cargo = crear_cargo_tienda(total, descripcion_cargo, folio, ip_cliente=ip_cliente)
        if not resultado_cargo["ok"]:
            return jsonify({"error": resultado_cargo["error"]}), 400
        openpay_charge_id = resultado_cargo["chargeId"]
        openpay_referencia = resultado_cargo.get("referencia")
        openpay_barcode_url = resultado_cargo.get("barcodeUrl")
        openpay_charge_data = resultado_cargo["cuerpo"]
        openpay_estado_pago = resultado_cargo["estado"]
        usa_openpay_para_este_metodo = True
    elif metodo_pago == "transferencia" and openpay_configurado():
        # Con credenciales reales, "transferencia" ya no pide
        # comprobante -- Openpay genera una CLABE/referencia unica por
        # pedido, asi que el pago se empareja solo (webhook/consulta
        # activa), igual que tarjeta/tiendas-aliadas. Mientras no haya
        # credenciales, cae al flujo manual de siempre mas abajo (sin
        # este bloque).
        resultado_cargo = crear_cargo_spei(total, descripcion_cargo, folio, ip_cliente=ip_cliente)
        if not resultado_cargo["ok"]:
            return jsonify({"error": resultado_cargo["error"]}), 400
        openpay_charge_id = resultado_cargo["chargeId"]
        openpay_referencia = resultado_cargo.get("referencia")
        openpay_banco = resultado_cargo.get("banco")
        openpay_clabe = resultado_cargo.get("clabe")
        openpay_fecha_vencimiento = resultado_cargo.get("fechaVencimiento")
        openpay_charge_data = resultado_cargo["cuerpo"]
        openpay_estado_pago = resultado_cargo["estado"]
        usa_openpay_para_este_metodo = True

    # Un producto/paquete guardado en el carrito de un cliente desde
    # antes no se revisa contra nada hasta este momento -- si el admin
    # lo oculta despues de que ya estaba en un carrito, el pedido debe
    # rechazarse aqui aunque el aviso del carrito (carrito.html) no se
    # haya visto o se haya saltado. Se revisa el id tal cual lo mando
    # el cliente (paquete o individual) ANTES de expandirlo, porque un
    # paquete oculto puede tener sus productos individuales todavia
    # activos -- expandir_items_a_individuales por si solo no lo
    # detectaria.
    for item in items:
        try:
            producto_id_directo = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        producto_directo = db.session.query(Producto).filter_by(id=producto_id_directo).first()
        if not producto_directo or not producto_directo.activo:
            nombre = producto_directo.nombre if producto_directo else "Uno de los productos de tu pedido"
            return jsonify({"error": "Por su gran éxito, \"" + nombre + "\" no está disponible por el momento. En breve tendremos más."}), 400

    # Validar inventario -- se hace siempre, para rechazar el pedido
    # completo si a algun producto ya no le alcanza, sin importar el
    # metodo de pago. Los paquetes ya no llevan su propio contador de
    # existencias: expandir_items_a_individuales los convierte en los
    # productos individuales reales que hay que descontar (ver
    # COMPOSICION_PAQUETES en models.py).
    productos_a_descontar = []
    for producto_id, cantidad in expandir_items_a_individuales(items):
        producto = db.session.query(Producto).filter_by(id=producto_id).first()
        if not producto:
            continue
        if not producto.activo:
            return jsonify({"error": "Por su gran éxito, \"" + producto.nombre + "\" no está disponible por el momento. En breve tendremos más."}), 400
        if producto.stock < cantidad:
            # Se deja un registro fijo para el admin (no un simple
            # aviso pasajero) -- asi no se pierde la señal de que se
            # esta rechazando una venta real por falta de existencias,
            # aunque nadie tenga el panel abierto justo en ese momento.
            db.session.add(AvisoStock(
                producto_id=producto.id,
                producto_nombre=producto.nombre,
                cantidad_solicitada=cantidad,
                cantidad_disponible=producto.stock,
            ))
            db.session.commit()
            return jsonify({"error": "Por su gran éxito, \"" + producto.nombre + "\" no está disponible por el momento. En breve tendremos más."}), 400
        productos_a_descontar.append((producto, cantidad))

    # El inventario solo se descuenta de una vez si este pedido no
    # depende de una confirmacion asincrona de Openpay (transferencia
    # manual con comprobante, revisada a mano), o si Openpay ya
    # confirmo el cobro como "completed" al crear el cargo mismo (el
    # caso normal de tarjeta). Si el cargo quedo en cualquier otro
    # estado -- tiendas aliadas y transferencia SPEI siempre (se pagan
    # despues, en efectivo o desde el banco), o una tarjeta que regreso
    # "in_progress"/un valor no documentado -- el stock se descuenta
    # despues, solo cuando se confirme de verdad el pago (ver
    # pagos_confirmacion.confirmar_pago_si_corresponde, llamada desde
    # el webhook y desde la consulta activa de respaldo). Asi no se
    # reserva inventario por pedidos que quiza nunca se paguen.
    stock_descontado = not usa_openpay_para_este_metodo or openpay_estado_pago == "completed"
    if stock_descontado:
        for producto, cantidad in productos_a_descontar:
            producto.stock -= cantidad

    usuario_id = None
    if datos_token and datos_token.get("tipo") == "usuario":
        usuario_id = datos_token.get("usuarioId")

    pedido = Pedido(
        folio=folio,
        usuario_id=usuario_id,
        items=items,
        total=total,
        metodo_pago=metodo_pago,
        datos_entrega=datos_entrega,
        comprobante_nombre=comprobante_nombre,
        comprobante_tipo=comprobante_tipo,
        comprobante_datos=comprobante_datos,
        openpay_charge_id=openpay_charge_id,
        openpay_referencia=openpay_referencia,
        openpay_barcode_url=openpay_barcode_url,
        openpay_charge_data=openpay_charge_data,
        openpay_estado_pago=openpay_estado_pago,
        openpay_clabe=openpay_clabe,
        openpay_banco=openpay_banco,
        openpay_fecha_vencimiento=openpay_fecha_vencimiento,
        stock_descontado=stock_descontado,
    )
    db.session.add(pedido)
    db.session.commit()

    correo_cliente = (datos_entrega or {}).get("email")
    if correo_cliente:
        enviar_correo_confirmacion_pedido(correo_cliente, folio, items, float(total))
    enviar_correo_nuevo_pedido_admin(folio, items, float(total), metodo_pago)

    return jsonify({"ok": True, "pedido": pedido.to_dict()})


def consultar_pedido_publico(body):
    folio = (body.get("folio") or "").strip().upper()
    correo = (body.get("email") or "").strip().lower()

    if not folio or not correo:
        return jsonify({"error": "Falta el folio o el correo."}), 400

    pedido = db.session.query(Pedido).filter_by(folio=folio).first()
    # Mismo mensaje si el folio no existe o si el correo no coincide,
    # para no revelar cual de los dos esta mal a quien esta adivinando.
    if not pedido or (pedido.datos_entrega or {}).get("email", "").strip().lower() != correo:
        return jsonify({"ok": False, "error": "No encontramos un pedido con ese folio y correo."})

    # Respaldo para cuando Openpay no puede entregar el webhook (nunca
    # en desarrollo local, ya que exige una URL publica) -- al
    # consultar el pedido se vuelve a preguntar el estado real. No-op
    # si el pedido no tiene cargo de Openpay o ya esta confirmado.
    confirmar_pago_si_corresponde(pedido)

    d = pedido.datos_entrega or {}
    return jsonify({
        "ok": True,
        "pedido": {
            "folio": pedido.folio,
            "estado": pedido.estado,
            "items": pedido.items,
            "total": float(pedido.total),
            "metodoPago": pedido.metodo_pago,
            "creadoEn": pedido.creado_en.isoformat(),
            "ciudad": d.get("ciudad"),
            "estadoDireccion": d.get("estado"),
        },
    })


def listar_kpis_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    pedidos = db.session.query(Pedido).all()
    total_usuarios = db.session.query(Usuario).count()
    productos = db.session.query(Producto).all()
    producto_por_id = {p.id: p for p in productos}
    producto_por_nombre = {p.nombre: p for p in productos}

    ventas_totales = sum(float(p.total) for p in pedidos)
    total_pedidos = len(pedidos)
    ticket_promedio = ventas_totales / total_pedidos if total_pedidos > 0 else 0

    por_metodo = {}
    # Se agrupa por id del item (no por nombre) porque es el mismo
    # identificador estable que ya usa expandir_items_a_individuales
    # para descontar inventario -- el nombre snapshot que trae cada
    # pedido puede quedar desactualizado si el producto se renombro
    # despues (visto en datos reales: un mismo id 1250 trae "Cápsulas
    # Premium" en un pedido viejo y "Paquete 1" en uno reciente), asi
    # que para mostrar se usa el nombre ACTUAL del catalogo cuando el
    # id todavia existe, y el nombre del pedido solo si ya no.
    por_producto = {}
    for p in pedidos:
        metodo = p.metodo_pago or "Sin especificar"
        por_metodo[metodo] = por_metodo.get(metodo, 0) + float(p.total)
        for item in (p.items or []):
            nombre_pedido = item.get("name") or "Producto sin nombre"
            cantidad = item.get("qty") or 0
            precio = item.get("price") or 0
            try:
                item_id = int(item.get("id"))
            except (TypeError, ValueError):
                item_id = None
            clave = item_id if item_id is not None else ("nombre:" + nombre_pedido)
            if clave not in por_producto:
                nombre_actual = producto_por_id[item_id].nombre if item_id in producto_por_id else nombre_pedido
                por_producto[clave] = {"id": item_id, "nombre": nombre_actual, "cantidad": 0, "monto": 0.0}
            por_producto[clave]["cantidad"] += cantidad
            por_producto[clave]["monto"] += cantidad * float(precio)

    producto_mas_vendido = (
        max(por_producto.values(), key=lambda v: v["cantidad"]) if por_producto else None
    )
    ventas_por_metodo = [{"metodo": m, "total": t} for m, t in sorted(por_metodo.items(), key=lambda par: -par[1])]
    ventas_por_producto = sorted(por_producto.values(), key=lambda v: -v["cantidad"])

    # Seccion (individual/paquete) de cada producto vendido: se cruza
    # primero por id contra el catalogo real (Producto.id) -- si un
    # pedido viejo trae un id que ya no existe (producto borrado), se
    # intenta un segundo cruce por nombre antes de asumir 'individual'
    # por default, para que ningun monto se pierda del total.
    seccion_individual = {"unidades": 0, "monto": 0.0}
    seccion_paquete = {"unidades": 0, "monto": 0.0}
    por_paquete = {
        pid: {
            "id": pid,
            "nombre": producto_por_id[pid].nombre if pid in producto_por_id else None,
            "unidades": 0,
            "monto": 0.0,
        }
        for pid in COMPOSICION_PAQUETES
    }
    for entrada in ventas_por_producto:
        producto = producto_por_id.get(entrada["id"]) if entrada["id"] is not None else None
        if producto is None:
            producto = producto_por_nombre.get(entrada["nombre"])
        if producto is not None and producto.seccion == "paquete":
            seccion_paquete["unidades"] += entrada["cantidad"]
            seccion_paquete["monto"] += entrada["monto"]
            if producto.id in por_paquete:
                por_paquete[producto.id]["unidades"] += entrada["cantidad"]
                por_paquete[producto.id]["monto"] += entrada["monto"]
        else:
            seccion_individual["unidades"] += entrada["cantidad"]
            seccion_individual["monto"] += entrada["monto"]

    ventas_por_seccion = {
        "individual": seccion_individual,
        "paquete": dict(seccion_paquete, porPaquete=list(por_paquete.values())),
    }

    return jsonify({
        "ventasTotales": ventas_totales,
        "totalPedidos": total_pedidos,
        "ticketPromedio": ticket_promedio,
        "totalUsuarios": total_usuarios,
        "productoMasVendido": (
            {"nombre": producto_mas_vendido["nombre"], "cantidad": producto_mas_vendido["cantidad"]}
            if producto_mas_vendido else None
        ),
        "ventasPorMetodo": ventas_por_metodo,
        "ventasPorProducto": [
            {"nombre": e["nombre"], "cantidad": e["cantidad"], "monto": e["monto"]}
            for e in ventas_por_producto
        ],
        "ventasPorSeccion": ventas_por_seccion,
    })


def listar_direcciones(datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    direcciones = (
        db.session.query(Direccion)
        .filter_by(usuario_id=datos_token.get("usuarioId"))
        .order_by(Direccion.creado_en.desc())
        .all()
    )
    return jsonify({"direcciones": [d.to_dict() for d in direcciones]})


def guardar_direccion(body, datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    calle = body.get("calle")
    colonia = body.get("colonia")
    cp = body.get("cp")
    ciudad = body.get("ciudad")
    estado = body.get("estado")

    if not calle or not colonia or not cp or not ciudad or not estado:
        return jsonify({"error": "Faltan datos obligatorios de la dirección."}), 400

    direccion_id = body.get("id")
    if direccion_id:
        direccion = db.session.query(Direccion).filter_by(
            id=direccion_id, usuario_id=datos_token.get("usuarioId")
        ).first()
        if not direccion:
            return jsonify({"error": "Dirección no encontrada."}), 404
    else:
        direccion = Direccion(usuario_id=datos_token.get("usuarioId"))
        db.session.add(direccion)

    direccion.etiqueta = body.get("etiqueta") or ""
    direccion.calle = calle
    direccion.colonia = colonia
    direccion.cp = cp
    direccion.ciudad = ciudad
    direccion.estado = estado
    direccion.referencias = body.get("referencias") or ""
    db.session.commit()

    return jsonify({"ok": True, "direccion": direccion.to_dict()})


def eliminar_direccion(body, datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    direccion = (
        db.session.query(Direccion)
        .filter_by(id=body.get("id"), usuario_id=datos_token.get("usuarioId"))
        .first()
    )
    if not direccion:
        return jsonify({"error": "Dirección no encontrada."}), 404

    db.session.delete(direccion)
    db.session.commit()
    return jsonify({"ok": True})


def actualizar_perfil(body, datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    usuario = db.session.query(Usuario).filter_by(id=datos_token.get("usuarioId")).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado."}), 404

    nombre = body.get("nombre")
    correo = body.get("correo")
    telefono = body.get("telefono")

    if not nombre or not correo:
        return jsonify({"error": "Nombre y correo son obligatorios."}), 400

    if correo != usuario.correo:
        existente = db.session.query(Usuario).filter_by(correo=correo).first()
        if existente:
            return jsonify({"ok": False, "error": "Ya hay otra cuenta con ese correo."})

    usuario.nombre = nombre
    usuario.correo = correo
    usuario.telefono = telefono or ""
    db.session.commit()

    token = firmar_token({"usuarioId": usuario.id, "correo": usuario.correo, "tipo": "usuario"})
    return jsonify({"ok": True, "token": token, "usuario": usuario.to_dict()})


def solicitar_cambio_password(body, datos_token):
    # Funciona en dos contextos: (a) desde "Mi cuenta", con sesion
    # activa (datos_token trae el correo, se ignora lo que venga en el
    # body); (b) desde "Olvide mi contraseña" en el login, sin sesion,
    # con el correo escrito a mano en el body.
    if datos_token and datos_token.get("tipo") == "usuario":
        correo = db.session.query(Usuario).filter_by(id=datos_token.get("usuarioId")).first().correo
    else:
        correo = body.get("correo")

    if not correo:
        return jsonify({"error": "Falta el correo."}), 400

    usuario = db.session.query(Usuario).filter_by(correo=correo).first()

    # Respuesta identica exista o no la cuenta -- si dijera "ese correo
    # no existe" cualquiera podria usar este formulario para averiguar
    # que correos estan registrados en el sitio.
    mensaje_generico = "Si el correo está registrado, se envió un enlace de confirmación."

    if usuario:
        token_crudo = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token_crudo.encode("utf-8")).hexdigest()
        expira_en = datetime.now(timezone.utc) + timedelta(minutes=30)

        db.session.add(TokenRestablecer(usuario_id=usuario.id, token_hash=token_hash, expira_en=expira_en))
        db.session.commit()

        enviar_correo_restablecer(usuario.correo, token_crudo)

    return jsonify({"ok": True, "mensaje": mensaje_generico})


def confirmar_cambio_password(body):
    token_crudo = body.get("token")
    password_nueva = body.get("passwordNueva") or ""

    if not token_crudo:
        return jsonify({"ok": False, "error": "Falta el token."}), 400
    if len(password_nueva) < 6:
        return jsonify({"ok": False, "error": "La nueva contraseña debe tener al menos 6 caracteres."})

    token_hash = hashlib.sha256(token_crudo.encode("utf-8")).hexdigest()
    fila = db.session.query(TokenRestablecer).filter_by(token_hash=token_hash).first()

    ahora = datetime.now(timezone.utc)
    if not fila or fila.usado_en is not None or fila.expira_en < ahora:
        return jsonify({"ok": False, "error": "El enlace no es válido o ya expiró. Solicita uno nuevo."})

    usuario = db.session.query(Usuario).filter_by(id=fila.usuario_id).first()
    usuario.password_hash = bcrypt.hashpw(password_nueva.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    fila.usado_en = ahora
    db.session.commit()

    return jsonify({"ok": True})


def mis_pedidos(datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    pedidos = (
        db.session.query(Pedido)
        .filter_by(usuario_id=datos_token.get("usuarioId"))
        .order_by(Pedido.creado_en.desc())
        .all()
    )

    resultado = []
    for p in pedidos:
        confirmar_pago_si_corresponde(p)
        d = p.to_dict()
        calificados = db.session.query(Opinion.producto_id).filter_by(pedido_id=p.id).all()
        d["productosCalificados"] = [c[0] for c in calificados]
        resultado.append(d)

    return jsonify({"pedidos": resultado})


def listar_tarjetas(datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    tarjetas = (
        db.session.query(Tarjeta)
        .filter_by(usuario_id=datos_token.get("usuarioId"))
        .order_by(Tarjeta.creado_en.desc())
        .all()
    )
    return jsonify({"tarjetas": [t.to_dict() for t in tarjetas]})


def guardar_tarjeta(body, datos_token):
    # Solo acepta marca/ultimos4/vencimiento -- nunca un numero de
    # tarjeta completo ni CVV (ni siquiera existe ese campo aqui).
    # Es una vista previa para cuando se conecte una pasarela de pago
    # real: ese dia, estos datos los llenara automaticamente la
    # respuesta de tokenizacion de la pasarela, no un formulario a mano.
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    marca = body.get("marca")
    ultimos4 = body.get("ultimos4") or ""
    vencimiento = body.get("vencimiento")

    if not marca or not vencimiento or not (ultimos4.isdigit() and len(ultimos4) == 4):
        return jsonify({"error": "Datos de tarjeta inválidos."}), 400

    tarjeta = Tarjeta(
        usuario_id=datos_token.get("usuarioId"),
        marca=marca,
        ultimos4=ultimos4,
        vencimiento=vencimiento,
    )
    db.session.add(tarjeta)
    db.session.commit()
    return jsonify({"ok": True, "tarjeta": tarjeta.to_dict()})


def eliminar_tarjeta(body, datos_token):
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    tarjeta = (
        db.session.query(Tarjeta)
        .filter_by(id=body.get("id"), usuario_id=datos_token.get("usuarioId"))
        .first()
    )
    if not tarjeta:
        return jsonify({"error": "Tarjeta no encontrada."}), 404

    db.session.delete(tarjeta)
    db.session.commit()
    return jsonify({"ok": True})


def listar_pedidos_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    pedidos = db.session.query(Pedido).order_by(Pedido.creado_en.desc()).all()

    resultado = []
    for p in pedidos:
        d = p.to_dict()
        if p.usuario_id:
            usuario = db.session.query(Usuario).filter_by(id=p.usuario_id).first()
            d["clienteCorreo"] = usuario.correo if usuario else None
        else:
            d["clienteCorreo"] = None
        resultado.append(d)

    return jsonify({"pedidos": resultado})


def _serializar_producto(p):
    """Igual que p.to_dict(), pero para un paquete el stock/disponible
    que se le muestra al cliente (o al admin) no es su propio contador
    -- que ya no se usa -- sino cuantas veces se puede armar con el
    stock ACTUAL de sus productos individuales (ver
    COMPOSICION_PAQUETES/calcular_stock_paquete en models.py)."""
    d = p.to_dict()
    stock_paquete = calcular_stock_paquete(p.id, db.session)
    if stock_paquete is not None:
        d["stock"] = stock_paquete
        d["disponible"] = p.activo and stock_paquete > 0
    return d


def listar_productos_publico():
    productos = (
        db.session.query(Producto)
        .filter_by(activo=True)
        .order_by(Producto.seccion, Producto.orden, Producto.id)
        .all()
    )
    return jsonify({"productos": [_serializar_producto(p) for p in productos]})


def listar_productos_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    productos = db.session.query(Producto).order_by(Producto.seccion, Producto.orden, Producto.id).all()
    return jsonify({"productos": [_serializar_producto(p) for p in productos]})


def crear_producto(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    nombre = (body.get("nombre") or "").strip()
    precio = body.get("precio")
    if not nombre or precio is None:
        return jsonify({"error": "Faltan datos del producto."}), 400

    precio_regular = body.get("precioRegular")
    producto = Producto(
        nombre=nombre,
        precio=precio,
        precio_regular=precio_regular if precio_regular not in (None, "") else None,
        imagen=body.get("imagen") or "",
        stock=int(body.get("stock") or 0),
        seccion=body.get("seccion") or "individual",
        insignia=body.get("insignia") or None,
        orden=int(body.get("orden") or 0),
    )
    db.session.add(producto)
    db.session.commit()
    return jsonify({"ok": True, "producto": _serializar_producto(producto)})


def actualizar_producto(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    producto = db.session.query(Producto).filter_by(id=body.get("id")).first()
    if not producto:
        return jsonify({"error": "Producto no encontrado."}), 404

    if "nombre" in body:
        producto.nombre = body["nombre"]
    if "precio" in body:
        producto.precio = body["precio"]
    if "precioRegular" in body:
        precio_regular = body["precioRegular"]
        producto.precio_regular = precio_regular if precio_regular not in (None, "") else None
    if "imagen" in body:
        producto.imagen = body["imagen"]
    if "stock" in body:
        producto.stock = int(body["stock"])
    if "seccion" in body:
        producto.seccion = body["seccion"]
    if "insignia" in body:
        producto.insignia = body["insignia"] or None
    if "orden" in body:
        producto.orden = int(body["orden"])
    if "activo" in body:
        producto.activo = bool(body["activo"])

    db.session.commit()
    return jsonify({"ok": True, "producto": _serializar_producto(producto)})


def listar_planes_suscripcion_publico():
    planes = (
        db.session.query(PlanSuscripcion)
        .filter_by(activo=True)
        .order_by(PlanSuscripcion.orden, PlanSuscripcion.frecuencia_dias)
        .all()
    )
    return jsonify({"planes": [p.to_dict() for p in planes]})


def listar_planes_suscripcion_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    planes = db.session.query(PlanSuscripcion).order_by(PlanSuscripcion.orden, PlanSuscripcion.frecuencia_dias).all()
    return jsonify({"planes": [p.to_dict() for p in planes]})


def crear_plan_suscripcion(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    nombre = (body.get("nombre") or "").strip()
    frecuencia_dias = body.get("frecuenciaDias")
    if not nombre or not frecuencia_dias:
        return jsonify({"error": "Faltan datos del plan (nombre y frecuencia)."}), 400

    plan = PlanSuscripcion(
        nombre=nombre,
        frecuencia_dias=int(frecuencia_dias),
        descuento_porcentaje=body.get("descuentoPorcentaje") or 0,
        descripcion=body.get("descripcion") or "",
        destacado=bool(body.get("destacado")),
        orden=int(body.get("orden") or 0),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify({"ok": True, "plan": plan.to_dict()})


def actualizar_plan_suscripcion(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    plan = db.session.query(PlanSuscripcion).filter_by(id=body.get("id")).first()
    if not plan:
        return jsonify({"error": "Plan no encontrado."}), 404

    if "nombre" in body:
        plan.nombre = body["nombre"]
    if "frecuenciaDias" in body:
        plan.frecuencia_dias = int(body["frecuenciaDias"])
    if "descuentoPorcentaje" in body:
        plan.descuento_porcentaje = body["descuentoPorcentaje"]
    if "descripcion" in body:
        plan.descripcion = body["descripcion"] or ""
    if "destacado" in body:
        plan.destacado = bool(body["destacado"])
    if "orden" in body:
        plan.orden = int(body["orden"])
    if "activo" in body:
        plan.activo = bool(body["activo"])

    db.session.commit()
    return jsonify({"ok": True, "plan": plan.to_dict()})


def _serializar_suscripcion_admin(s, usuario, producto, plan):
    return {
        "id": s.id,
        "usuarioId": s.usuario_id,
        "clienteNombre": usuario.nombre if usuario else "Cliente eliminado",
        "clienteCorreo": usuario.correo if usuario else "",
        "productoId": s.producto_id,
        "productoNombre": producto.nombre if producto else "Producto eliminado",
        "productoStock": producto.stock if producto else 0,
        "planId": s.plan_id,
        "planNombre": plan.nombre if plan else "Plan eliminado",
        "frecuenciaDias": plan.frecuencia_dias if plan else None,
        "precioEntrega": float(s.precio_entrega),
        "estado": s.estado,
        "proximaEntrega": s.proxima_entrega.isoformat() if s.proxima_entrega else None,
        "notas": s.notas,
        "creadoEn": s.creado_en.isoformat(),
    }


def listar_suscripciones_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    suscripciones = db.session.query(Suscripcion).order_by(Suscripcion.creado_en.desc()).all()
    usuarios = {u.id: u for u in db.session.query(Usuario).all()}
    productos = {p.id: p for p in db.session.query(Producto).all()}
    planes = {p.id: p for p in db.session.query(PlanSuscripcion).all()}
    return jsonify({
        "suscripciones": [
            _serializar_suscripcion_admin(
                s, usuarios.get(s.usuario_id), productos.get(s.producto_id), planes.get(s.plan_id)
            )
            for s in suscripciones
        ]
    })


def crear_suscripcion_admin(body, datos_token):
    """El admin da de alta a mano la suscripcion de un cliente que ya
    tiene cuenta (por ahora no hay flujo de autoservicio en
    suscripciones.html -- ver comentario en el modelo Suscripcion)."""
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    correo = (body.get("correo") or "").strip()
    producto_id = body.get("productoId")
    plan_id = body.get("planId")
    if not correo or not producto_id or not plan_id:
        return jsonify({"error": "Faltan datos de la suscripción (correo, producto y plan)."}), 400

    usuario = db.session.query(Usuario).filter_by(correo=correo).first()
    if not usuario:
        return jsonify({"error": "No existe ningún cliente registrado con ese correo."}), 404

    producto = db.session.query(Producto).filter_by(id=producto_id).first()
    if not producto:
        return jsonify({"error": "Producto no encontrado."}), 404

    plan = db.session.query(PlanSuscripcion).filter_by(id=plan_id).first()
    if not plan:
        return jsonify({"error": "Plan no encontrado."}), 404

    precio_entrega = body.get("precioEntrega")
    if precio_entrega in (None, ""):
        precio_entrega = round(float(producto.precio) * (1 - float(plan.descuento_porcentaje) / 100), 2)

    proxima_entrega = None
    if body.get("proximaEntrega"):
        try:
            proxima_entrega = datetime.strptime(body["proximaEntrega"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Fecha de próxima entrega inválida."}), 400

    suscripcion = Suscripcion(
        usuario_id=usuario.id,
        producto_id=producto.id,
        plan_id=plan.id,
        precio_entrega=precio_entrega,
        proxima_entrega=proxima_entrega,
        notas=body.get("notas") or "",
    )
    db.session.add(suscripcion)
    db.session.commit()
    return jsonify({
        "ok": True,
        "suscripcion": _serializar_suscripcion_admin(suscripcion, usuario, producto, plan),
    })


def actualizar_suscripcion_admin(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    suscripcion = db.session.query(Suscripcion).filter_by(id=body.get("id")).first()
    if not suscripcion:
        return jsonify({"error": "Suscripción no encontrada."}), 404

    if "precioEntrega" in body:
        suscripcion.precio_entrega = body["precioEntrega"]
    if "estado" in body:
        if body["estado"] not in ("activa", "pausada", "cancelada"):
            return jsonify({"error": "Estado inválido."}), 400
        suscripcion.estado = body["estado"]
    if "planId" in body:
        plan_nuevo = db.session.query(PlanSuscripcion).filter_by(id=body["planId"]).first()
        if not plan_nuevo:
            return jsonify({"error": "Plan no encontrado."}), 404
        suscripcion.plan_id = plan_nuevo.id
    if "proximaEntrega" in body:
        valor = body["proximaEntrega"]
        if valor:
            try:
                suscripcion.proxima_entrega = datetime.strptime(valor, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Fecha de próxima entrega inválida."}), 400
        else:
            suscripcion.proxima_entrega = None
    if "notas" in body:
        suscripcion.notas = body["notas"] or ""

    db.session.commit()
    usuario = db.session.query(Usuario).filter_by(id=suscripcion.usuario_id).first()
    producto = db.session.query(Producto).filter_by(id=suscripcion.producto_id).first()
    plan = db.session.query(PlanSuscripcion).filter_by(id=suscripcion.plan_id).first()
    return jsonify({"ok": True, "suscripcion": _serializar_suscripcion_admin(suscripcion, usuario, producto, plan)})


def registrar_entrega_suscripcion(body, datos_token):
    """Registra manualmente el ciclo de entrega/cobro de una
    suscripcion: crea un Pedido real (aparece en el tab Pedidos igual
    que una compra normal) y descuenta inventario -- mismas reglas que
    crear_pedido (producto activo, stock suficiente, aviso persistente
    si no alcanza, ver AvisoStock). Existe porque el cobro recurrente
    automatico todavia no esta conectado (ver Suscripcion en
    models.py); en cuanto lo este, esta accion puede quedar tal cual
    para registros manuales/excepciones."""
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    suscripcion = db.session.query(Suscripcion).filter_by(id=body.get("id")).first()
    if not suscripcion:
        return jsonify({"error": "Suscripción no encontrada."}), 404
    if suscripcion.estado != "activa":
        return jsonify({"error": "Solo se pueden registrar entregas de suscripciones activas."}), 400

    producto = db.session.query(Producto).filter_by(id=suscripcion.producto_id).first()
    if not producto or not producto.activo:
        return jsonify({"error": "El producto de esta suscripción ya no está disponible."}), 400
    if producto.stock < 1:
        db.session.add(AvisoStock(
            producto_id=producto.id,
            producto_nombre=producto.nombre,
            cantidad_solicitada=1,
            cantidad_disponible=producto.stock,
        ))
        db.session.commit()
        return jsonify({"error": "Por su gran éxito, \"" + producto.nombre + "\" no está disponible por el momento. En breve tendremos más."}), 400

    usuario = db.session.query(Usuario).filter_by(id=suscripcion.usuario_id).first()
    direccion = (
        db.session.query(Direccion)
        .filter_by(usuario_id=suscripcion.usuario_id)
        .order_by(Direccion.creado_en.desc())
        .first()
    )
    datos_entrega = {
        "nombre": usuario.nombre if usuario else "",
        "telefono": usuario.telefono if usuario else "",
        "calle": direccion.calle if direccion else "",
        "colonia": direccion.colonia if direccion else "",
        "ciudad": direccion.ciudad if direccion else "",
        "estado": direccion.estado if direccion else "",
        "cp": direccion.cp if direccion else "",
    }

    producto.stock -= 1

    folio = generar_folio()
    while db.session.query(Pedido).filter_by(folio=folio).first():
        folio = generar_folio()

    pedido = Pedido(
        folio=folio,
        usuario_id=suscripcion.usuario_id,
        items=[{"id": producto.id, "name": producto.nombre, "qty": 1, "price": float(suscripcion.precio_entrega)}],
        total=suscripcion.precio_entrega,
        metodo_pago="suscripción",
        estado="Aceptado",
        datos_entrega=datos_entrega,
        stock_descontado=True,
    )
    db.session.add(pedido)

    plan = db.session.query(PlanSuscripcion).filter_by(id=suscripcion.plan_id).first()
    frecuencia = plan.frecuencia_dias if plan else 30
    base = suscripcion.proxima_entrega or datetime.now(timezone.utc).date()
    suscripcion.proxima_entrega = base + timedelta(days=frecuencia)

    db.session.commit()
    return jsonify({
        "ok": True,
        "pedido": pedido.to_dict(),
        "suscripcion": _serializar_suscripcion_admin(suscripcion, usuario, producto, plan),
    })


def listar_avisos_stock(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    avisos = (
        db.session.query(AvisoStock)
        .filter_by(revisado=False)
        .order_by(AvisoStock.creado_en.desc())
        .all()
    )
    return jsonify({"avisos": [a.to_dict() for a in avisos]})


def marcar_avisos_stock_revisados(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    db.session.query(AvisoStock).filter_by(revisado=False).update({"revisado": True})
    db.session.commit()
    return jsonify({"ok": True})


def obtener_comprobante_pedido(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    pedido = db.session.query(Pedido).filter_by(id=body.get("id")).first()
    if not pedido or not pedido.comprobante_datos:
        return jsonify({"error": "Este pedido no tiene comprobante adjunto."}), 404

    return jsonify({
        "ok": True,
        "nombre": pedido.comprobante_nombre,
        "tipo": pedido.comprobante_tipo,
        "datosBase64": pedido.comprobante_datos,
    })


def _ajustar_inventario(items, signo):
    """signo=+1 regresa stock al inventario (pedido se cancela).
    signo=-1 lo vuelve a descontar (se revierte una cancelacion,
    volviendo el pedido a un estado activo). Igual que en crear_pedido,
    los paquetes se resuelven contra sus productos individuales."""
    for producto_id, cantidad in expandir_items_a_individuales(items):
        producto = db.session.query(Producto).filter_by(id=producto_id).first()
        if not producto:
            continue
        producto.stock = max(0, producto.stock + signo * cantidad)


def actualizar_estado_pedido(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    estado = body.get("estado")
    if estado not in ESTADOS_PEDIDO:
        return jsonify({"error": "Estado inválido."}), 400

    pedido = db.session.query(Pedido).filter_by(id=body.get("id")).first()
    if not pedido:
        return jsonify({"error": "Pedido no encontrado."}), 404

    estado_cambio = estado != pedido.estado
    if estado_cambio:
        # Un pedido de tarjeta/tienda que todavia no confirma su pago
        # con Openpay (ver pagos_confirmacion.py) nunca llego a
        # descontar inventario -- si se cancela antes de eso, no hay
        # nada que restaurar. Se usa stock_descontado (no el metodo de
        # pago) para saber si de verdad se le quito stock a este
        # pedido.
        if estado == "Cancelado" and pedido.stock_descontado:
            _ajustar_inventario(pedido.items, 1)
            pedido.stock_descontado = False
        elif pedido.estado == "Cancelado" and not pedido.stock_descontado:
            _ajustar_inventario(pedido.items, -1)
            pedido.stock_descontado = True

    pedido.estado = estado
    db.session.commit()

    if estado_cambio:
        correo_cliente = (pedido.datos_entrega or {}).get("email")
        enviar_correo_cambio_estado_pedido(correo_cliente, pedido.folio, estado)

    return jsonify({"ok": True, "pedido": pedido.to_dict()})


def nueva_opinion(body, datos_token):
    # Solo clientes con sesion iniciada pueden opinar -- ya no es
    # anonimo/publico (pedido de Marcos, para filtrar mas quien opina).
    # El nombre se toma SIEMPRE de la cuenta real, nunca de lo que
    # venga en el body, para que no se pueda opinar con un nombre falso.
    if not exigir_tipo(datos_token, "usuario"):
        return jsonify({"error": "Debes iniciar sesión para dejar tu opinión."}), 401

    usuario = db.session.query(Usuario).filter_by(id=datos_token.get("usuarioId")).first()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado."}), 404

    estrellas = body.get("estrellas")
    texto = body.get("texto")
    producto_id = body.get("productoId")
    producto_nombre = body.get("productoNombre")
    pedido_id = body.get("pedidoId")

    if not texto or not isinstance(estrellas, int) or not (1 <= estrellas <= 5):
        return jsonify({"error": "Faltan datos obligatorios o la calificación no es válida (1-5)."}), 400

    if pedido_id is not None:
        # Calificar un producto de un pedido puntual exige ademas que
        # el pedido sea realmente del usuario que la esta enviando --
        # si no, cualquiera podria mandar pedidoId de otra persona.
        pedido = db.session.query(Pedido).filter_by(id=pedido_id).first()
        if not pedido or pedido.usuario_id != usuario.id:
            return jsonify({"error": "Ese pedido no te pertenece."}), 403

        ya_existe = (
            db.session.query(Opinion)
            .filter_by(pedido_id=pedido_id, producto_id=producto_id)
            .first()
        )
        if ya_existe:
            return jsonify({"ok": False, "error": "Ya calificaste este producto de este pedido."})

    opinion = Opinion(
        nombre=usuario.nombre,
        estrellas=estrellas,
        texto=texto,
        estado="pendiente",
        producto_id=producto_id,
        producto_nombre=producto_nombre,
        pedido_id=pedido_id,
        usuario_id=usuario.id,
    )
    db.session.add(opinion)
    db.session.commit()
    return jsonify({"ok": True})


def listar_opiniones_publicas():
    opiniones = (
        db.session.query(Opinion)
        .filter_by(estado="aprobado")
        .order_by(Opinion.creado_en.desc())
        .all()
    )
    return jsonify({"opiniones": [o.to_dict() for o in opiniones]})


def calificaciones_por_producto():
    opiniones = (
        db.session.query(Opinion)
        .filter(Opinion.estado == "aprobado", Opinion.producto_id.isnot(None))
        .all()
    )

    agregados = {}
    for o in opiniones:
        a = agregados.setdefault(o.producto_id, {"suma": 0, "total": 0})
        a["suma"] += o.estrellas
        a["total"] += 1

    resultado = {
        pid: {"promedio": round(a["suma"] / a["total"], 1), "total": a["total"]}
        for pid, a in agregados.items()
    }
    return jsonify({"calificaciones": resultado})


def listar_opiniones_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    opiniones = db.session.query(Opinion).order_by(Opinion.creado_en.desc()).all()
    return jsonify({"opiniones": [o.to_dict() for o in opiniones]})


def cambiar_estado_opinion(body, datos_token, desde, hasta):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    opinion = db.session.query(Opinion).filter_by(id=body.get("id"), estado=desde).first()
    if not opinion:
        return jsonify({"error": f"La opinión no está en estado '{desde}' (puede que ya se haya actualizado)."}), 409

    opinion.estado = hasta
    db.session.commit()
    return jsonify({"ok": True})


def eliminar_opinion(body, datos_token, desde):
    # rechazar_opinion (desde pendiente) y eliminar_opinion (desde
    # oculto) son ambas un borrado fisico -- irreversible, por eso el
    # frontend pide confirmacion antes de llamarlas.
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    opinion = db.session.query(Opinion).filter_by(id=body.get("id"), estado=desde).first()
    if not opinion:
        return jsonify({"error": f"La opinión no está en estado '{desde}' (puede que ya se haya actualizado)."}), 409

    db.session.delete(opinion)
    db.session.commit()
    return jsonify({"ok": True})
