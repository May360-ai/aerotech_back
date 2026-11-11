from flask import Flask
from flask_cors import CORS
from app.routes.auth_routes import auth_bp
from app.routes.vuelos_routes import vuelos_bp
from app.routes.reservas_routes import reservas_bp

def create_app():
    app = Flask(__name__)
    
    # Habilitar CORS para permitir peticiones desde Flutter (Web, Android, iOS)
    CORS(app)

    # Registro de módulos SOA bajo el prefijo /api
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(vuelos_bp, url_prefix="/api")
    app.register_blueprint(reservas_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return {
            "servicio": "AeroTech API REST",
            "arquitectura": "SOA (Service-Oriented Architecture)",
            "estado": "En línea",
            "entorno": "UTA - Aplicaciones Distribuidas"
        }

    return app