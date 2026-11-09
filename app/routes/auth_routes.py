from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
import jwt
from database import get_db_connection
from app.middlewares.auth import hash_password
from config import Config

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/usuarios/registro", methods=["POST"])
def registrar_usuario():
    datos = request.get_json(silent=True) or {}
    nombre = datos.get("nombre")
    correo = datos.get("correo")
    cedula_ruc = datos.get("cedula_ruc")
    password = datos.get("password")

    if not all([nombre, correo, cedula_ruc, password]):
        return jsonify({"estado": "error", "mensaje": "Todos los campos son obligatorios"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
            if cur.fetchone():
                return jsonify({"estado": "error", "mensaje": "El correo ya está registrado"}), 409

            pwd_hash = hash_password(password)
            cur.execute(
                """
                INSERT INTO usuarios (nombre, correo, cedula_ruc, password_hash)
                VALUES (%s, %s, %s, %s) RETURNING id, nombre, correo
                """,
                (nombre, correo, cedula_ruc, pwd_hash)
            )
            nuevo_usuario = cur.fetchone()
            conn.commit()
            return jsonify({"estado": "exito", "usuario": nuevo_usuario}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": str(e)}), 500
    finally:
        conn.close()

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True) or {}
    correo = datos.get("correo")
    password = datos.get("password")

    if not correo or not password:
        return jsonify({"estado": "error", "mensaje": "Credenciales incompletas"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            pwd_hash = hash_password(password)
            cur.execute(
                "SELECT id, nombre, correo, cedula_ruc FROM usuarios WHERE correo = %s AND password_hash = %s",
                (correo, pwd_hash)
            )
            usuario = cur.fetchone()
            if not usuario:
                return jsonify({"estado": "error", "mensaje": "Credenciales inválidas"}), 401

            expiracion = datetime.now(timezone.utc) + timedelta(hours=8)
            token = jwt.encode(
                {"usuario_id": usuario["id"], "correo": usuario["correo"], "exp": expiracion},
                Config.JWT_SECRET,
                algorithm="HS256"
            )

            cur.execute(
                "INSERT INTO tokens (usuario_id, token, expiracion) VALUES (%s, %s, %s)",
                (usuario["id"], token, expiracion)
            )
            conn.commit()

            return jsonify({"estado": "exito", "token": token, "usuario": usuario}), 200
    finally:
        conn.close()