import hashlib
from functools import wraps
from flask import request, jsonify
import jwt
from config import Config

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def token_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({
                "estado": "error", 
                "mensaje": "Token de autenticación faltante o no proporcionado"
            }), 401

        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            request.user_id = payload["usuario_id"]
            request.user_email = payload.get("correo")
        except jwt.ExpiredSignatureError:
            return jsonify({
                "estado": "error", 
                "mensaje": "La sesión ha expirado. Inicie sesión nuevamente."
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "estado": "error", 
                "mensaje": "Token de autenticación inválido o corrupto"
            }), 401

        return f(*args, **kwargs)
    return decorador