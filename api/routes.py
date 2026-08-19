import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from flask import Blueprint, request, jsonify
from auth import firmar_token, verificar_token
from db import db
from email_utils import enviar_correo_restablecer
from models import Usuario, Admin, Pedido, Direccion, Tarjeta, TokenRestablecer, Opinion

bp = Blueprint("accion", __name__)

ESTADOS_PEDIDO = {"Pendiente", "Aceptado", "Enviado", "Entregado", "Cancelado"}

ACCIONES_PUBLICAS = {
    "registro_usuario", "login_usuario", "login_admin", "crear_pedido",
    "solicitar_cambio_password", "confirmar_cambio_password",
    "nueva_opinion", "listar_opiniones_publicas",
}


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
        if tipo_accion == "nueva_opinion":
            return nueva_opinion(body)
        if tipo_accion == "listar_opiniones_publicas":
            return listar_opiniones_publicas()
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
        print(f"[accion:{tipo_accion}]", error)
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


def crear_pedido(body, datos_token):
    items = body.get("items")
    total = body.get("total")
    metodo_pago = body.get("metodoPago") or ""
    datos_entrega = body.get("datosEntrega")

    if not items or total is None or not datos_entrega:
        return jsonify({"error": "Pedido inválido."}), 400

    usuario_id = None
    if datos_token and datos_token.get("tipo") == "usuario":
        usuario_id = datos_token.get("usuarioId")

    pedido = Pedido(
        usuario_id=usuario_id,
        items=items,
        total=total,
        metodo_pago=metodo_pago,
        datos_entrega=datos_entrega,
    )
    db.session.add(pedido)
    db.session.commit()

    return jsonify({"ok": True, "pedido": pedido.to_dict()})


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

    direccion = Direccion(
        usuario_id=datos_token.get("usuarioId"),
        etiqueta=body.get("etiqueta") or "",
        calle=calle,
        colonia=colonia,
        cp=cp,
        ciudad=ciudad,
        estado=estado,
        referencias=body.get("referencias") or "",
    )
    db.session.add(direccion)
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
    return jsonify({"pedidos": [p.to_dict() for p in pedidos]})


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


def actualizar_estado_pedido(body, datos_token):
    if not exigir_tipo(datos_token, "admin"):
        return jsonify({"error": "No tienes permiso para hacer esto."}), 403

    estado = body.get("estado")
    if estado not in ESTADOS_PEDIDO:
        return jsonify({"error": "Estado inválido."}), 400

    pedido = db.session.query(Pedido).filter_by(id=body.get("id")).first()
    if not pedido:
        return jsonify({"error": "Pedido no encontrado."}), 404

    pedido.estado = estado
    db.session.commit()
    return jsonify({"ok": True, "pedido": pedido.to_dict()})


def nueva_opinion(body):
    nombre = body.get("nombre")
    estrellas = body.get("estrellas")
    texto = body.get("texto")

    if not nombre or not texto or not isinstance(estrellas, int) or not (1 <= estrellas <= 5):
        return jsonify({"error": "Faltan datos obligatorios o la calificación no es válida (1-5)."}), 400

    opinion = Opinion(nombre=nombre, estrellas=estrellas, texto=texto, estado="pendiente")
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
