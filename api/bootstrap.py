import os
import bcrypt
from db import db
from models import Admin


def crear_admin_inicial_si_hace_falta():
    usuario = os.environ.get("ADMIN_USUARIO")
    password = os.environ.get("ADMIN_PASSWORD")

    if db.session.query(Admin).count() > 0:
        return

    if not usuario or not password:
        print("[bootstrap] No hay admins y no se definieron ADMIN_USUARIO/ADMIN_PASSWORD; omitiendo creación.")
        return

    hash_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.session.add(Admin(usuario=usuario, password_hash=hash_password))
    db.session.commit()
    print(f"[bootstrap] Admin inicial creado: {usuario}")
