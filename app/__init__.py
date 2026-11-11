import datetime
from decimal import Decimal
from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS

from app.routes.auth_routes import auth_bp
from app.routes.vuelos_routes import vuelos_bp
from app.routes.reservas_routes import reservas_bp
from app.routes.admin_routes import admin_bp

class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def create_app():
    app = Flask(__name__)
    
    app.json_provider_class = CustomJSONProvider
    app.json = CustomJSONProvider(app)

    CORS(app)

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(vuelos_bp, url_prefix="/api")
    app.register_blueprint(reservas_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return {
            "servicio": "AeroTech API REST",
            "arquitectura": "SOA",
            "estado": "En línea"
        }

    return app