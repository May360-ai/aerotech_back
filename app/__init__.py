from flask import Flask
from flask_cors import CORS
from app.routes.auth_routes import auth_bp
from app.routes.vuelos_routes import vuelos_bp
from app.routes.reservas_routes import reservas_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Registrar los módulos (Blueprints)
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(vuelos_bp, url_prefix="/api")
    app.register_blueprint(reservas_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return {
            "servicio": "AeroTech API REST",
            "arquitectura": "SOA",
            "estado": "En línea"
        }

    return app