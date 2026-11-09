import hashlib
from functools import wraps
from flask import request, jsonify
import jwt
from config import Config

def hash_password(password: str) -> str:
    """Devuelve el hash SHA-256 de una contraseña."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def token_requerido(f):
    """Middleware para validar la presencia y validez del token JWT."""
    @wraps(f)
    def decorador(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"estado": "error", "mensaje": "Token de autenticación faltante"}), 401

        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            request.user_id = payload["usuario_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"estado": "error", "mensaje": "El token ha expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"estado": "error", "mensaje": "Token inválido o corrupto"}), 401

        return f(*args, **kwargs)
    return decorador