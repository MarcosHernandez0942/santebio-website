import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def build_database_uri():
    usuario = os.environ["PGUSER"]
    password = os.environ["PGPASSWORD"]
    host = os.environ["PGHOST"]
    puerto = os.environ["PGPORT"]
    base = os.environ["PGDATABASE"]
    return f"postgresql+psycopg2://{usuario}:{password}@{host}:{puerto}/{base}"
