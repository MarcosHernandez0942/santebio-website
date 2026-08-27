import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from db import db, build_database_uri
from routes import bp as accion_bp
from bootstrap import crear_admin_inicial_si_hace_falta, crear_productos_iniciales_si_hace_falta

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db.init_app(app)
app.register_blueprint(accion_bp, url_prefix="/api")

with app.app_context():
    db.create_all()
    crear_admin_inicial_si_hace_falta()
    crear_productos_iniciales_si_hace_falta()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4931))
    app.run(host="0.0.0.0", port=port)
