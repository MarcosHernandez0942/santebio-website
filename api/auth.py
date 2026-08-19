import os
from datetime import datetime, timedelta, timezone
import jwt

SECRETO = os.environ.get("JWT_SECRET")

if not SECRETO:
    raise RuntimeError("Falta definir JWT_SECRET en las variables de entorno.")


def firmar_token(payload):
    datos = dict(payload)
    datos["exp"] = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode(datos, SECRETO, algorithm="HS256")


def verificar_token(token):
    try:
        return jwt.decode(token, SECRETO, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
