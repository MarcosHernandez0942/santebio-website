import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from db import db, build_database_uri
from routes import bp as accion_bp
from bootstrap import (
    crear_admin_inicial_si_hace_falta,
    crear_productos_iniciales_si_hace_falta,
    agregar_columnas_openpay_si_hace_falta,
    agregar_columna_precio_regular_si_hace_falta,
    crear_planes_suscripcion_iniciales_si_hace_falta,
    migrar_planes_suscripcion_a_producto_especifico_si_hace_falta,
)
from webhook_openpay import bp as openpay_webhook_bp
from routes_pdf import bp as pdf_bp

app = Flask(__name__)
CORS(app)

# En produccion el sitio corre detras de un proxy/CDN (ya se sabe por
# el bug de auto-reload resuelto en una sesion anterior) -- sin esto,
# request.remote_addr daria la IP del proxy en vez de la del cliente
# real, y Openpay pide la IP real del cliente para antifraude en cada
# cargo (ver api/openpay_client.py).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db.init_app(app)
app.register_blueprint(accion_bp, url_prefix="/api")
app.register_blueprint(openpay_webhook_bp, url_prefix="/api")
app.register_blueprint(pdf_bp, url_prefix="/api")

with app.app_context():
    migrar_planes_suscripcion_a_producto_especifico_si_hace_falta()
    db.create_all()
    agregar_columnas_openpay_si_hace_falta()
    agregar_columna_precio_regular_si_hace_falta()
    crear_admin_inicial_si_hace_falta()
    crear_productos_iniciales_si_hace_falta()
    crear_planes_suscripcion_iniciales_si_hace_falta()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4931))
    app.run(host="0.0.0.0", port=port)
