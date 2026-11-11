import re
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from database import get_db_connection
from app.middlewares.auth import token_requerido, admin_requerido

admin_bp = Blueprint("admin_bp", __name__)

REGEX_SOLO_LETRAS = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\(\)\-\.]+$")
REGEX_IATA = re.compile(r"^[A-Z]{3}$")
REGEX_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

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
                    u["fecha_registro"] = str(u["fecha_registro"])
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
        return jsonify({"estado": "error", "mensaje": "El nombre de la ciudad y el código IATA son obligatorios"}), 400

    if len(nombre) < 3 or len(nombre) > 50:
        return jsonify({"estado": "error", "mensaje": "El nombre debe tener entre 3 y 50 caracteres"}), 400

    if not REGEX_SOLO_LETRAS.match(nombre):
        return jsonify({"estado": "error", "mensaje": "El nombre solo puede contener letras y espacios (sin emojis ni números)"}), 400

    if not REGEX_IATA.match(codigo_iata):
        return jsonify({"estado": "error", "mensaje": "El código IATA debe constar de exactamente 3 letras mayúsculas (ej. UIO)"}), 400

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
    except Exception:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": "El origen o código IATA ya se encuentra registrado"}), 409
    finally:
        conn.close()


@admin_bp.route("/admin/vuelos", methods=["POST"])
@token_requerido
@admin_requerido
def crear_vuelo():
    datos = request.get_json(silent=True) or {}
    origen = str(datos.get("origen", "")).strip()
    destino = str(datos.get("destino", "")).strip()
    fecha_str = str(datos.get("fecha", "")).strip()
    hora_salida = str(datos.get("hora_salida", "")).strip()
    hora_llegada = str(datos.get("hora_llegada", "")).strip()
    precio_raw = datos.get("precio")
    asientos_raw = datos.get("asientos_totales", 40)

    if not all([origen, destino, fecha_str, hora_salida, hora_llegada, precio_raw]):
        return jsonify({"estado": "error", "mensaje": "Todos los campos del itinerario son obligatorios"}), 400

    if not REGEX_SOLO_LETRAS.match(origen) or not REGEX_SOLO_LETRAS.match(destino):
        return jsonify({"estado": "error", "mensaje": "Las ciudades de origen y destino no pueden contener emojis ni caracteres especiales"}), 400

    if origen.lower() == destino.lower():
        return jsonify({"estado": "error", "mensaje": "El origen y el destino no pueden ser la misma ciudad"}), 400

    try:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_obj < date.today():
            return jsonify({"estado": "error", "mensaje": "La fecha del vuelo no puede ser anterior al día de hoy"}), 400
    except ValueError:
        return jsonify({"estado": "error", "mensaje": "Formato de fecha inválido. Utilice el formato AAAA-MM-DD"}), 400

    if not REGEX_HORA.match(hora_salida[:5]) or not REGEX_HORA.match(hora_llegada[:5]):
        return jsonify({"estado": "error", "mensaje": "Formato de hora inválido. Utilice formato de 24 horas HH:MM"}), 400

    t_salida = datetime.strptime(hora_salida[:5], "%H:%M").time()
    t_llegada = datetime.strptime(hora_llegada[:5], "%H:%M").time()

    if t_salida >= t_llegada:
        return jsonify({
            "estado": "error", 
            "mensaje": f"Conflicto de itinerario: La hora de salida ({hora_salida[:5]}) debe ser previa a la hora de llegada ({hora_llegada[:5]})"
        }), 400

    try:
        precio = float(precio_raw)
        if precio <= 0:
            return jsonify({"estado": "error", "mensaje": "El precio del boleto debe ser mayor a \$0.00"}), 400
        if precio > 10000:
            return jsonify({"estado": "error", "mensaje": "El precio no puede exceder los \$10,000.00"}), 400
    except (ValueError, TypeError):
        return jsonify({"estado": "error", "mensaje": "El precio debe ser un valor numérico decimal válido"}), 400

    try:
        asientos_totales = int(asientos_raw)
        if asientos_totales < 10 or asientos_totales > 350:
            return jsonify({"estado": "error", "mensaje": "La capacidad de la aeronave debe estar entre 10 y 350 asientos"}), 400
    except (ValueError, TypeError):
        return jsonify({"estado": "error", "mensaje": "La capacidad de asientos debe ser un número entero válido"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vuelos (origen, destino, fecha, hora_salida, hora_llegada, precio, asientos_disponibles, asientos_totales)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, origen, destino, fecha, hora_salida, hora_llegada, precio, asientos_disponibles, asientos_totales
                """,
                (origen, destino, fecha_str, hora_salida[:5], hora_llegada[:5], round(precio, 2), asientos_totales, asientos_totales)
            )
            nuevo_vuelo = cur.fetchone()
            conn.commit()

            nuevo_vuelo["fecha"] = str(nuevo_vuelo["fecha"])
            nuevo_vuelo["hora_salida"] = str(nuevo_vuelo["hora_salida"])
            nuevo_vuelo["hora_llegada"] = str(nuevo_vuelo["hora_llegada"])
            nuevo_vuelo["precio"] = float(nuevo_vuelo["precio"])

            return jsonify({"estado": "exito", "vuelo": nuevo_vuelo}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": f"Error al crear vuelo: {str(e)}"}), 500
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
    except Exception:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": "No se puede eliminar el vuelo porque tiene reservas emitidas"}), 409
    finally:
        conn.close()