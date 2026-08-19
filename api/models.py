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
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "usuarioId": self.usuario_id,
            "items": self.items,
            "total": float(self.total),
            "metodoPago": self.metodo_pago,
            "estado": self.estado,
            "datosEntrega": self.datos_entrega,
            "creadoEn": self.creado_en.isoformat(),
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
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "estrellas": self.estrellas,
            "texto": self.texto,
            "estado": self.estado,
            "creadoEn": self.creado_en.isoformat(),
        }


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
