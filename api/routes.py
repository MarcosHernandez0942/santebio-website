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
from models import Usuario, Admin, Pedido, Direccion, Tarjeta, TokenRestablecer, Opinion, Producto

bp = Blueprint("accion", __name__)

ESTADOS_PEDIDO = {"Pendiente", "Aceptado", "Enviado", "Entregado", "Cancelado"}

ACCIONES_PUBLICAS = {
    "registro_usuario", "login_usuario", "login_admin", "crear_pedido",
    "solicitar_cambio_password", "confirmar_cambio_password",
    "listar_opiniones_publicas", "calificaciones_por_producto",
    "consultar_pedido_publico", "listar_productos_publico",
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

    if not items or total is None or not datos_entrega:
        return jsonify({"error": "Pedido inválido."}), 400

    comprobante_nombre = comprobante_tipo = comprobante_datos = None
    if comprobante:
        comprobante_datos = comprobante.get("datosBase64")
        if comprobante_datos and len(comprobante_datos) > MAX_COMPROBANTE_BASE64:
            return jsonify({"error": "El comprobante es demasiado grande (máximo 5 MB)."}), 400
        comprobante_nombre = comprobante.get("nombre")
        comprobante_tipo = comprobante.get("tipo")

    # Validar y descontar inventario ANTES de crear el pedido -- si a
    # algun producto ya no le alcanza el stock, se rechaza todo el
    # pedido en vez de dejarlo a medias.
    productos_a_descontar = []
    for item in items:
        try:
            producto_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        cantidad = item.get("qty") or 0
        producto = db.session.query(Producto).filter_by(id=producto_id).first()
        if not producto:
            continue
        if producto.stock < cantidad:
            return jsonify({"error": "Ya no hay suficiente inventario de \"" + producto.nombre + "\"."}), 400
        productos_a_descontar.append((producto, cantidad))

    for producto, cantidad in productos_a_descontar:
        producto.stock -= cantidad

    usuario_id = None
    if datos_token and datos_token.get("tipo") == "usuario":
        usuario_id = datos_token.get("usuarioId")

    folio = generar_folio()
    # Practicamente imposible que choque, pero por si acaso se
    # regenera en vez de fallar el pedido.
    while db.session.query(Pedido).filter_by(folio=folio).first():
        folio = generar_folio()

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

    ventas_totales = sum(float(p.total) for p in pedidos)
    total_pedidos = len(pedidos)
    ticket_promedio = ventas_totales / total_pedidos if total_pedidos > 0 else 0

    por_metodo = {}
    por_producto = {}
    for p in pedidos:
        metodo = p.metodo_pago or "Sin especificar"
        por_metodo[metodo] = por_metodo.get(metodo, 0) + float(p.total)
        for item in (p.items or []):
            nombre = item.get("name") or "Producto sin nombre"
            cantidad = item.get("qty") or 0
            por_producto[nombre] = por_producto.get(nombre, 0) + cantidad

    producto_mas_vendido = max(por_producto.items(), key=lambda par: par[1]) if por_producto else None
    ventas_por_metodo = [{"metodo": m, "total": t} for m, t in sorted(por_metodo.items(), key=lambda par: -par[1])]

    return jsonify({
        "ventasTotales": ventas_totales,
        "totalPedidos": total_pedidos,
        "ticketPromedio": ticket_promedio,
        "totalUsuarios": total_usuarios,
        "productoMasVendido": (
            {"nombre": producto_mas_vendido[0], "cantidad": producto_mas_vendido[1]}
            if producto_mas_vendido else None
        ),
        "ventasPorMetodo": ventas_por_metodo,
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


def listar_productos_publico():
    productos = (
        db.session.query(Producto)
        .filter_by(activo=True)
        .order_by(Producto.seccion, Producto.orden, Producto.id)
        .all()
    )
    return jsonify({"productos": [p.to_dict() for p in productos]})


def listar_productos_admin(datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para ver esto."}), 403

    productos = db.session.query(Producto).order_by(Producto.seccion, Producto.orden, Producto.id).all()
    return jsonify({"productos": [p.to_dict() for p in productos]})


def crear_producto(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    nombre = (body.get("nombre") or "").strip()
    precio = body.get("precio")
    if not nombre or precio is None:
        return jsonify({"error": "Faltan datos del producto."}), 400

    producto = Producto(
        nombre=nombre,
        precio=precio,
        imagen=body.get("imagen") or "",
        stock=int(body.get("stock") or 0),
        seccion=body.get("seccion") or "individual",
        insignia=body.get("insignia") or None,
        orden=int(body.get("orden") or 0),
    )
    db.session.add(producto)
    db.session.commit()
    return jsonify({"ok": True, "producto": producto.to_dict()})


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
    return jsonify({"ok": True, "producto": producto.to_dict()})


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
    volviendo el pedido a un estado activo)."""
    for item in items:
        try:
            producto_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        producto = db.session.query(Producto).filter_by(id=producto_id).first()
        if not producto:
            continue
        producto.stock = max(0, producto.stock + signo * (item.get("qty") or 0))


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
        if estado == "Cancelado":
            _ajustar_inventario(pedido.items, 1)
        elif pedido.estado == "Cancelado":
            _ajustar_inventario(pedido.items, -1)

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
