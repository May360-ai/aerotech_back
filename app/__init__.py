from flask import Flask
from flask_cors import CORS
from app.routes.auth_routes import auth_bp
from app.routes.vuelos_routes import vuelos_bp
from app.routes.reservas_routes import reservas_bp
from app.routes.admin_routes import admin_bp 

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(vuelos_bp, url_prefix="/api")
    app.register_blueprint(reservas_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")  

    return app