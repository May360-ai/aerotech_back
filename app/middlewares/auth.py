import hashlib
from functools import wraps
from flask import request, jsonify
import jwt
from config import Config
from database import get_db_connection

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
            return jsonify({"estado": "error", "mensaje": "Token de autenticación faltante"}), 401

        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            user_id = payload["usuario_id"]

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT activo, rol FROM usuarios WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    return jsonify({"estado": "error", "mensaje": "Usuario no encontrado"}), 401
                if not user["activo"]:
                    return jsonify({"estado": "error", "mensaje": "Tu cuenta ha sido desactivada por un administrador"}), 403

            request.user_id = user_id
            request.user_email = payload.get("correo")
            request.user_rol = user["rol"]

        except jwt.ExpiredSignatureError:
            return jsonify({"estado": "error", "mensaje": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"estado": "error", "mensaje": "Token inválido"}), 401
        finally:
            conn.close()

        return f(*args, **kwargs)
    return decorador

def admin_requerido(f):
    """Restringe la ruta exclusivamente a usuarios con rol 'admin'."""
    @wraps(f)
    def decorador(*args, **kwargs):
        if getattr(request, "user_rol", "") != "admin":
            return jsonify({"estado": "error", "mensaje": "Acceso denegado: se requieren privilegios de Administrador"}), 403
        return f(*args, **kwargs)
    return decorador