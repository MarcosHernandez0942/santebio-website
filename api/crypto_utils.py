import json
import os
from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, Text

_LLAVE = os.environ.get("ENCRYPTION_KEY")

if not _LLAVE:
    raise RuntimeError("Falta definir ENCRYPTION_KEY en las variables de entorno.")

_fernet = Fernet(_LLAVE.encode("utf-8"))


def encriptar(texto):
    if texto is None:
        return None
    return _fernet.encrypt(texto.encode("utf-8")).decode("utf-8")


def desencriptar(texto):
    if texto is None:
        return None
    return _fernet.decrypt(texto.encode("utf-8")).decode("utf-8")


class CampoEncriptado(TypeDecorator):
    """Encripta un campo de texto antes de guardarlo (AES via Fernet) y
    lo desencripta automaticamente al leerlo por el ORM -- el resto
    del codigo (routes.py, to_dict()) nunca ve ni maneja el texto
    encriptado, solo el valor real. Se usa en columnas con informacion
    personal (nombre, telefono, direccion, tarjetas), NO en columnas
    que se buscan con filter_by/where (ej. correo de login), porque el
    texto cifrado no es determinista y no se puede indexar/buscar."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encriptar(value)

    def process_result_value(self, value, dialect):
        return desencriptar(value)


class JSONEncriptado(TypeDecorator):
    """Igual que CampoEncriptado pero para columnas JSON (ej. la
    direccion de entrega guardada dentro de un pedido)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encriptar(json.dumps(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(desencriptar(value))
