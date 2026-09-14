from datetime import datetime, timezone
from db import db
from crypto_utils import CampoEncriptado, JSONEncriptado


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(CampoEncriptado, nullable=False)
    # correo se queda SIN encriptar a proposito: es la llave que se usa
    # para buscar al hacer login (filter_by(correo=...)) y el cifrado
    # de Fernet no es determinista (el mismo correo produce un texto
    # cifrado distinto cada vez), asi que no se puede indexar/buscar
    # encriptado sin un esquema aparte (ej. un hash determinista extra).
    correo = db.Column(db.Text, unique=True, nullable=False)
    telefono = db.Column(CampoEncriptado, nullable=False, default="")
    password_hash = db.Column(db.Text, nullable=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "correo": self.correo,
            "telefono": self.telefono,
        }


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    # Folio publico para que un cliente SIN cuenta pueda dar seguimiento
    # a su pedido (folio + correo) sin iniciar sesion. Aparte del id
    # interno a proposito: el id es secuencial (facil de adivinar,
    # "pedido 5", "pedido 6"...), el folio es aleatorio.
    folio = db.Column(db.Text, unique=True, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    items = db.Column(db.JSON, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    metodo_pago = db.Column(db.Text, nullable=False, default="")
    # Ciclo de vida que usa el panel de admin para dar seguimiento:
    # Pendiente (recien llega, falta aceptarlo) -> Aceptado -> Enviado
    # -> Entregado. Cancelado es un estado aparte para cuando el
    # cliente cancela o no hay inventario suficiente.
    estado = db.Column(db.Text, nullable=False, default="Pendiente")
    # Trae nombre/telefono/direccion completos del cliente -> se
    # encripta todo el bloque.
    datos_entrega = db.Column(JSONEncriptado, nullable=False)
    # Comprobante de transferencia (imagen o PDF), guardado como base64
    # y encriptado -- igual de sensible que un dato bancario, asi que
    # se trata igual que el resto de la info personal del pedido. Se
    # separa de to_dict() a proposito (ver comprobante_pendiente abajo)
    # para no mandar el archivo completo cada vez que el admin carga el
    # listado de pedidos -- solo se pide bajo demanda, ver la accion
    # "obtener_comprobante_pedido" en routes.py.
    comprobante_nombre = db.Column(CampoEncriptado, nullable=True)
    comprobante_tipo = db.Column(CampoEncriptado, nullable=True)
    comprobante_datos = db.Column(CampoEncriptado, nullable=True)
    # Datos del cargo de Openpay (tarjeta o pago en tienda/Paynet). No
    # son sensibles como un numero de tarjeta -- son solo el id del
    # cargo y, para pago en tienda, la referencia/codigo de barras que
    # el cliente necesita para pagar -- asi que van sin encriptar,
    # igual que folio/estado/metodoPago.
    openpay_charge_id = db.Column(db.Text, nullable=True)
    openpay_referencia = db.Column(db.Text, nullable=True)
    openpay_barcode_url = db.Column(db.Text, nullable=True)
    openpay_estado_pago = db.Column(db.Text, nullable=True)
    # Datos de la CLABE de transferencia SPEI (metodo "transferencia"
    # cuando ya hay credenciales reales de Openpay) -- mismo criterio
    # que arriba, no son sensibles (a diferencia de un numero de
    # tarjeta): son la cuenta a la que el propio cliente debe
    # depositar, no una cuenta suya.
    openpay_clabe = db.Column(db.Text, nullable=True)
    openpay_banco = db.Column(db.Text, nullable=True)
    openpay_fecha_vencimiento = db.Column(db.Text, nullable=True)
    # Respuesta cruda completa del ultimo cargo/consulta a Openpay, sin
    # recortar -- para no perder informacion si Openpay agrega un
    # campo que el codigo todavia no espera explicitamente. No se
    # expone en to_dict() a proposito (mismo criterio que
    # comprobante_datos: el cliente no necesita ver esto).
    openpay_charge_data = db.Column(db.JSON, nullable=True)
    # Hace idempotente el descuento de inventario diferido: el pago de
    # tarjeta/tienda solo descuenta stock hasta que Openpay CONFIRMA el
    # cobro (no al crear el cargo) -- y esa confirmacion puede llegar
    # por el webhook o por la consulta activa de respaldo, a veces mas
    # de una vez para el mismo pedido, asi que se marca aqui para no
    # descontar el stock dos veces.
    stock_descontado = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "folio": self.folio,
            "usuarioId": self.usuario_id,
            "items": self.items,
            "total": float(self.total),
            "metodoPago": self.metodo_pago,
            "estado": self.estado,
            "datosEntrega": self.datos_entrega,
            "creadoEn": self.creado_en.isoformat(),
            "tieneComprobante": bool(self.comprobante_datos),
            "openpayChargeId": self.openpay_charge_id,
            "openpayReferencia": self.openpay_referencia,
            "openpayBarcodeUrl": self.openpay_barcode_url,
            "openpayEstadoPago": self.openpay_estado_pago,
            "openpayClabe": self.openpay_clabe,
            "openpayBanco": self.openpay_banco,
            "openpayFechaVencimiento": self.openpay_fecha_vencimiento,
        }


class Direccion(db.Model):
    __tablename__ = "direcciones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    etiqueta = db.Column(CampoEncriptado, nullable=False, default="")
    calle = db.Column(CampoEncriptado, nullable=False)
    colonia = db.Column(CampoEncriptado, nullable=False)
    cp = db.Column(CampoEncriptado, nullable=False)
    ciudad = db.Column(CampoEncriptado, nullable=False)
    estado = db.Column(CampoEncriptado, nullable=False)
    referencias = db.Column(CampoEncriptado, nullable=False, default="")
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "etiqueta": self.etiqueta,
            "calle": self.calle,
            "colonia": self.colonia,
            "cp": self.cp,
            "ciudad": self.ciudad,
            "estado": self.estado,
            "referencias": self.referencias,
        }


class TokenRestablecer(db.Model):
    """Token de un solo uso para confirmar por correo el cambio de
    contraseña. Solo se guarda el HASH del token (sha256), nunca el
    token real -- igual que una contraseña, asi que aunque la base de
    datos se filtre, nadie puede usarlo para cambiar la contraseña de
    alguien. El token real solo existe en el correo que se envia."""

    __tablename__ = "tokens_restablecer"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    token_hash = db.Column(db.Text, unique=True, nullable=False)
    expira_en = db.Column(db.DateTime(timezone=True), nullable=False)
    usado_en = db.Column(db.DateTime(timezone=True), nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Opinion(db.Model):
    """Opiniones/reseñas de clientes -- mismo flujo de estados que se
    usa en visas_y_pasaportes_america: pendiente (recien enviada) ->
    aprobado (visible en publico) <-> oculto (aprobada pero escondida
    temporalmente). Desde pendiente tambien se puede rechazar (se
    borra). Desde oculto se puede eliminar (borrado permanente).
    Sin encriptar a proposito: son opiniones que se van a publicar en
    la pagina principal una vez aprobadas, no datos privados."""

    __tablename__ = "opiniones"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, nullable=False)
    estrellas = db.Column(db.Integer, nullable=False)
    texto = db.Column(db.Text, nullable=False)
    estado = db.Column(db.Text, nullable=False, default="pendiente")
    # Opcionales: si vienen, es una calificacion de un producto puntual
    # (normalmente desde un pedido ya entregado) en vez de una opinion
    # general del sitio. producto_nombre se guarda tal cual (no hay
    # tabla de productos) para poder mostrarlo sin depender de que el
    # catalogo de tienda.html no haya cambiado los nombres despues.
    producto_id = db.Column(db.Text, nullable=True)
    producto_nombre = db.Column(db.Text, nullable=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "estrellas": self.estrellas,
            "texto": self.texto,
            "estado": self.estado,
            "productoId": self.producto_id,
            "productoNombre": self.producto_nombre,
            "creadoEn": self.creado_en.isoformat(),
        }


class Producto(db.Model):
    """Catalogo real de la tienda -- antes vivia como HTML fijo en
    tienda.html (5 productos con ids 998/999/1250/1252/1253). Sin
    encriptar a proposito: es informacion publica del catalogo, no
    datos personales. El id se conserva igual al de los productos
    existentes al migrar, para no romper opiniones/calificaciones
    (Opinion.producto_id) ni pedidos historicos, que ya guardan estos
    ids como texto."""

    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    # Precio "de lista" antes del descuento -- si esta lleno y es mayor
    # al precio actual, la tienda lo muestra tachado en rojo arriba del
    # precio real (mismo estilo que ya tenia el inicio a mano para
    # 90/150 capsulas). Si es NULL, no se muestra ningun tachado -- el
    # admin lo deja vacio cuando no hay promocion activa.
    precio_regular = db.Column(db.Numeric(10, 2), nullable=True)
    imagen = db.Column(db.Text, nullable=False, default="")
    stock = db.Column(db.Integer, nullable=False, default=0)
    # activo=False es "ocultar" a proposito (temporada/tiempo limitado)
    # -- no se borra el producto, solo deja de mostrarse en la tienda.
    activo = db.Column(db.Boolean, nullable=False, default=True)
    # 'individual' (cuadricula de arriba) o 'paquete' (seccion de
    # abajo) -- misma separacion visual que ya tenia tienda.html.
    seccion = db.Column(db.Text, nullable=False, default="individual")
    insignia = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": float(self.precio),
            "precioRegular": float(self.precio_regular) if self.precio_regular is not None else None,
            "imagen": self.imagen,
            "stock": self.stock,
            "activo": self.activo,
            "seccion": self.seccion,
            "insignia": self.insignia,
            "orden": self.orden,
            "disponible": self.activo and self.stock > 0,
        }


# Que productos INDIVIDUALES (y cuantas unidades de cada uno) hay que
# descontar cuando se vende un paquete -- los paquetes ya no llevan su
# propio contador de existencias (pedido explicito del cliente): su
# disponibilidad y su descuento de inventario se resuelven siempre
# contra el stock real de los productos individuales que los componen.
# Si se agrega un paquete nuevo, hay que agregar aqui su composicion.
COMPOSICION_PAQUETES = {
    1250: [(998, 1), (999, 1)],  # 1 frasco de 150 + 1 de 90
    1252: [(998, 3)],            # 3x2 de 90 -> se entregan 3 frascos de 90
    1253: [(999, 3)],            # 3x2 de 150 -> se entregan 3 frascos de 150
}


def expandir_items_a_individuales(items):
    """Convierte los items de un pedido (que pueden incluir paquetes)
    en pares (producto_id, cantidad) de solo productos INDIVIDUALES --
    usado por crear_pedido/descontar_inventario/_ajustar_inventario
    para que un paquete siempre afecte el stock de sus componentes, no
    un contador propio."""
    expandido = {}
    for item in items or []:
        try:
            producto_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        cantidad = item.get("qty") or 0
        composicion = COMPOSICION_PAQUETES.get(producto_id)
        if composicion:
            for individual_id, unidades_por_paquete in composicion:
                expandido[individual_id] = expandido.get(individual_id, 0) + unidades_por_paquete * cantidad
        else:
            expandido[producto_id] = expandido.get(producto_id, 0) + cantidad
    return list(expandido.items())


def calcular_stock_paquete(producto_id, db_session):
    """Cuantas veces se puede vender este paquete con el stock ACTUAL
    de los productos individuales que lo componen (el minimo entre
    todos, ej. si necesita 1x90 y 1x150, y hay 90 de un lado y 5 del
    otro, solo alcanza para 5 paquetes). Regresa None si el id no
    corresponde a un paquete con composicion definida."""
    composicion = COMPOSICION_PAQUETES.get(producto_id)
    if not composicion:
        return None
    disponibles = []
    for individual_id, unidades_por_paquete in composicion:
        individual = db_session.query(Producto).filter_by(id=individual_id).first()
        if not individual:
            return 0
        disponibles.append(individual.stock // unidades_por_paquete)
    return min(disponibles) if disponibles else 0


class Tarjeta(db.Model):
    """Solo guarda metadatos NO sensibles de la tarjeta (marca, ultimos
    4 digitos, vencimiento) -- nunca el numero completo ni el CVV. El
    campo gateway_token queda listo para cuando se conecte una
    pasarela real (Stripe/Conekta/MercadoPago): ese token es lo que
    identifica la tarjeta ante la pasarela, y es lo unico necesario
    para cobrar despues -- el numero real nunca pasa ni se guarda
    aqui."""

    __tablename__ = "tarjetas"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    marca = db.Column(CampoEncriptado, nullable=False)
    ultimos4 = db.Column(CampoEncriptado, nullable=False)
    vencimiento = db.Column(CampoEncriptado, nullable=False)
    gateway_token = db.Column(CampoEncriptado, nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "marca": self.marca,
            "ultimos4": self.ultimos4,
            "vencimiento": self.vencimiento,
        }


class AvisoStock(db.Model):
    """Registro persistente de cada vez que un pedido se rechaza por
    falta de inventario -- a diferencia de un toast (que solo lo ve
    quien tenga el panel abierto en ese momento), esto se queda
    guardado en la base de datos hasta que el admin lo marca como
    revisado, para que no se pierda la señal de que se esta rechazando
    demanda real por falta de existencias."""

    __tablename__ = "avisos_stock"

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, nullable=False)
    producto_nombre = db.Column(db.Text, nullable=False)
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    cantidad_disponible = db.Column(db.Integer, nullable=False)
    revisado = db.Column(db.Boolean, nullable=False, default=False)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "productoId": self.producto_id,
            "productoNombre": self.producto_nombre,
            "cantidadSolicitada": self.cantidad_solicitada,
            "cantidadDisponible": self.cantidad_disponible,
            "revisado": self.revisado,
            "creadoEn": self.creado_en.isoformat(),
        }
