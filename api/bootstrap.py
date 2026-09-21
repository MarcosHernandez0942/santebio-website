import os
import bcrypt
from sqlalchemy import inspect as sa_inspect
from db import db
from models import Admin, Producto


def agregar_columnas_openpay_si_hace_falta():
    """db.create_all() solo crea tablas nuevas, no altera una tabla
    "pedidos" que ya existia antes de agregar los campos de Openpay a
    Pedido (models.py) -- por eso se agregan aqui a mano. Postgres
    soporta "IF NOT EXISTS" en ADD COLUMN, asi que correr esto en un
    despliegue que ya tiene las columnas no hace nada."""
    for columna in (
        "openpay_charge_id", "openpay_referencia", "openpay_barcode_url", "openpay_estado_pago",
        "openpay_clabe", "openpay_banco", "openpay_fecha_vencimiento",
    ):
        db.session.execute(db.text(f"ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS {columna} TEXT"))
    db.session.execute(db.text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS openpay_charge_data JSON"))
    db.session.execute(
        db.text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS stock_descontado BOOLEAN NOT NULL DEFAULT false")
    )
    db.session.commit()


def agregar_columna_precio_regular_si_hace_falta():
    """Igual que agregar_columnas_openpay_si_hace_falta: db.create_all()
    no altera una tabla "productos" que ya existia antes de agregar
    precio_regular a Producto (models.py)."""
    db.session.execute(db.text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS precio_regular NUMERIC(10, 2)"))
    db.session.commit()


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
    {"id": 998, "nombre": "90 Cápsulas", "precio": 269, "precio_regular": 310,
     "imagen": "wp-content/uploads/2026/03/1.webp",
     "stock": 100, "seccion": "individual", "insignia": None, "orden": 1},
    {"id": 999, "nombre": "150 Cápsulas", "precio": 399, "precio_regular": 480,
     "imagen": "wp-content/uploads/2026/03/1.webp",
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


def migrar_planes_suscripcion_a_combos_si_hace_falta():
    """Segundo rediseño de planes_suscripcion (para quien lea el
    historial de git: el primero fue producto+frecuencia+precio por
    plan). Pedido explicito de Marcos para simplificar: un plan ahora
    es un combo con NOMBRE propio, armado de uno o mas productos en
    las cantidades que el admin elija (ver PlanSuscripcionProducto),
    con precio y precio regular (igual que Producto), frecuencia y
    descripcion -- y se puede eliminar por completo, no solo ocultar.

    Como el feature todavia no tiene NINGUN suscriptor real (el cobro
    automatico ni siquiera esta conectado, ver Suscripcion en
    models.py), no hay datos de clientes que preservar -- por eso esta
    migracion reconstruye las tablas desde cero (y de paso borra los
    planes de ejemplo anteriores, pedido explicito: "quita todas las
    subs que ya estan") en vez de intentar mapear filas viejas a la
    estructura nueva. Si alguna vez llegan a existir suscripciones de
    clientes reales, este patron (DROP TABLE) ya no se puede volver a
    usar para el siguiente cambio de esquema."""
    inspector = sa_inspect(db.engine)
    if "planes_suscripcion" not in inspector.get_table_names():
        return  # tabla nueva, la crea db.create_all() con el esquema actual

    columnas = {c["name"] for c in inspector.get_columns("planes_suscripcion")}
    if "nombre" in columnas:
        return  # ya esta en el esquema nuevo

    db.session.execute(db.text("DROP TABLE IF EXISTS precios_plan_producto"))
    db.session.execute(db.text("DROP TABLE IF EXISTS plan_suscripcion_productos"))
    db.session.execute(db.text("DROP TABLE IF EXISTS suscripciones"))
    db.session.execute(db.text("DROP TABLE IF EXISTS planes_suscripcion"))
    db.session.commit()
    print("[bootstrap] Tablas de suscripciones reconstruidas con el esquema de combos (nombre + productos/cantidades + precio).")
