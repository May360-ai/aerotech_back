from flask import Blueprint, request, jsonify
from database import get_db_connection
from app.middlewares.auth import token_requerido, admin_requerido

admin_bp = Blueprint("admin_bp", __name__)

@admin_bp.route("/admin/usuarios", methods=["GET"])
@token_requerido
@admin_requerido
def listar_usuarios():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, correo, cedula_ruc, rol, activo, fecha_registro FROM usuarios ORDER BY id ASC")
            usuarios = cur.fetchall()
            for u in usuarios:
                if u.get("fecha_registro"):
                    u["fecha_registro"] = u["fecha_registro"].strftime("%Y-%m-%d %H:%M:%S")
            return jsonify(usuarios), 200
    finally:
        conn.close()

@admin_bp.route("/admin/usuarios/<int:user_id>/estado", methods=["PATCH"])
@token_requerido
@admin_requerido
def alternar_estado_usuario(user_id):
    datos = request.get_json(silent=True) or {}
    nuevo_estado = datos.get("activo")

    if nuevo_estado is None:
        return jsonify({"estado": "error", "mensaje": "Campo 'activo' requerido (true/false)"}), 400

    if user_id == request.user_id:
        return jsonify({"estado": "error", "mensaje": "Un administrador no puede desactivarse a sí mismo"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE usuarios SET activo = %s WHERE id = %s RETURNING id, nombre, activo", (nuevo_estado, user_id))
            usuario = cur.fetchone()
            if not usuario:
                return jsonify({"estado": "error", "mensaje": "Usuario no encontrado"}), 404
            conn.commit()
            return jsonify({"estado": "exito", "mensaje": "Estado actualizado", "usuario": usuario}), 200
    finally:
        conn.close()


@admin_bp.route("/origenes", methods=["GET"])
def listar_origenes():
    """Público: Lista los orígenes activos para filtros de búsqueda y creación de vuelos."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM origenes WHERE activo = true ORDER BY nombre ASC")
            return jsonify(cur.fetchall()), 200
    finally:
        conn.close()

@admin_bp.route("/admin/origenes", methods=["POST"])
@token_requerido
@admin_requerido
def crear_origen():
    datos = request.get_json(silent=True) or {}
    nombre = datos.get("nombre", "").strip()
    codigo_iata = datos.get("codigo_iata", "").strip().upper()

    if not nombre or not codigo_iata:
        return jsonify({"estado": "error", "mensaje": "Nombre y código IATA son obligatorios"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO origenes (nombre, codigo_iata) VALUES (%s, %s) RETURNING id, nombre, codigo_iata, activo",
                (nombre, codigo_iata)
            )
            nuevo = cur.fetchone()
            conn.commit()
            return jsonify({"estado": "exito", "origen": nuevo}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": "El origen o código IATA ya existe"}), 409
    finally:
        conn.close()

@admin_bp.route("/admin/origenes/<int:origen_id>", methods=["DELETE"])
@token_requerido
@admin_requerido
def desactivar_origen(origen_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE origenes SET activo = false WHERE id = %s RETURNING id", (origen_id,))
            if not cur.fetchone():
                return jsonify({"estado": "error", "mensaje": "Origen no encontrado"}), 404
            conn.commit()
            return jsonify({"estado": "exito", "mensaje": "Origen desactivado"}), 200
    finally:
        conn.close()


@admin_bp.route("/admin/vuelos", methods=["POST"])
@token_requerido
@admin_requerido
def crear_vuelo():
    datos = request.get_json(silent=True) or {}
    origen = datos.get("origen")
    destino = datos.get("destino")
    fecha = datos.get("fecha")
    hora_salida = datos.get("hora_salida")
    hora_llegada = datos.get("hora_llegada")
    precio = datos.get("precio")
    asientos_totales = datos.get("asientos_totales", 40)

    if not all([origen, destino, fecha, hora_salida, hora_llegada, precio]):
        return jsonify({"estado": "error", "mensaje": "Todos los campos del itinerario son obligatorios"}), 400

    if origen == destino:
        return jsonify({"estado": "error", "mensaje": "El origen y el destino no pueden ser iguales"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vuelos (origen, destino, fecha, hora_salida, hora_llegada, precio, asientos_disponibles, asientos_totales)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, origen, destino, fecha, hora_salida, hora_llegada, precio, asientos_disponibles, asientos_totales
                """,
                (origen, destino, fecha, hora_salida, hora_llegada, float(precio), int(asientos_totales), int(asientos_totales))
            )
            nuevo_vuelo = cur.fetchone()
            conn.commit()
            return jsonify({"estado": "exito", "vuelo": nuevo_vuelo}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": str(e)}), 500
    finally:
        conn.close()

@admin_bp.route("/admin/vuelos/<int:vuelo_id>", methods=["DELETE"])
@token_requerido
@admin_requerido
def eliminar_vuelo(vuelo_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM vuelos WHERE id = %s RETURNING id", (vuelo_id,))
            if not cur.fetchone():
                return jsonify({"estado": "error", "mensaje": "Vuelo no encontrado"}), 404
            conn.commit()
            return jsonify({"estado": "exito", "mensaje": "Vuelo eliminado"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": "No se puede eliminar: tiene reservas asociadas"}), 409
    finally:
        conn.close()