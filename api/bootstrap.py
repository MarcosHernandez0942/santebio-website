import os
import bcrypt
from db import db
from models import Admin, Producto


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


# Catalogo original de tienda.html antes de migrarlo a la tabla
# "productos" (ver Producto en models.py). Se conservan los mismos ids
# que ya tenia como HTML fijo (998/999/1250/1252/1253) porque
# Opinion.producto_id y los items guardados en pedidos historicos ya
# los referencian como texto -- cambiar los ids aqui rompe esos
# vinculos. Esto solo se usa para sembrar un despliegue NUEVO con la
# tabla vacia; en un entorno que ya tiene productos capturados a mano
# desde el panel de administrador, no se toca nada.
_PRODUCTOS_INICIALES = [
    {"id": 998, "nombre": "90 Cápsulas", "precio": 269, "imagen": "wp-content/uploads/2026/03/1.webp",
     "stock": 100, "seccion": "individual", "insignia": None, "orden": 1},
    {"id": 999, "nombre": "150 Cápsulas", "precio": 399, "imagen": "wp-content/uploads/2026/03/1.webp",
     "stock": 100, "seccion": "individual", "insignia": None, "orden": 2},
    {"id": 1250, "nombre": "Paquete 1 — 1 frasco de 150 + 1 de 90", "precio": 501,
     "imagen": "wp-content/uploads/2026/03/1.webp", "stock": 50, "seccion": "paquete",
     "insignia": None, "orden": 1},
    {"id": 1252, "nombre": "Paquete 2 — 3x2 de 90 cápsulas", "precio": 538,
     "imagen": "wp-content/uploads/2026/03/1.webp", "stock": 50, "seccion": "paquete",
     "insignia": "Ahorro especial", "orden": 2},
    {"id": 1253, "nombre": "Paquete 3 — 3x2 de 150 cápsulas", "precio": 798,
     "imagen": "wp-content/uploads/2026/03/1.webp", "stock": 50, "seccion": "paquete",
     "insignia": "Recomendado", "orden": 3},
]


def crear_productos_iniciales_si_hace_falta():
    if db.session.query(Producto).count() > 0:
        return

    for datos in _PRODUCTOS_INICIALES:
        db.session.add(Producto(**datos))
    db.session.commit()

    # Los ids de arriba son explicitos (no dejados al autoincrement),
    # asi que hay que adelantar la secuencia de Postgres manualmente --
    # si no, el siguiente producto que se agregue desde el panel de
    # admin intentaria reusar un id ya ocupado (ej. el 999) y fallaria.
    max_id = max(p["id"] for p in _PRODUCTOS_INICIALES)
    db.session.execute(
        db.text("SELECT setval('productos_id_seq', :max_id)"),
        {"max_id": max_id},
    )
    db.session.commit()
    print(f"[bootstrap] {len(_PRODUCTOS_INICIALES)} productos iniciales creados.")
