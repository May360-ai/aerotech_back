import re
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from database import get_db_connection
from app.middlewares.auth import token_requerido, admin_requerido

admin_bp = Blueprint("admin_bp", __name__)

REGEX_SOLO_LETRAS = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\(\)\-\.]+$")
REGEX_IATA = re.compile(r"^[A-Z]{3}$")
REGEX_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

# ==================== USUARIOS ====================

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
        return jsonify({"estado": "error", "mensaje": "Campo 'activo' requerido"}), 400

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

# ==================== ORÍGENES (CRUD + SOFT DELETE) ====================

@admin_bp.route("/origenes", methods=["GET"])
def listar_origenes():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM origenes WHERE activo = true ORDER BY nombre ASC")
            return jsonify(cur.fetchall()), 200
    finally:
        conn.close()

@admin_bp.route("/admin/origenes/todos", methods=["GET"])
@token_requerido
@admin_requerido
def listar_todos_origenes_admin():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM origenes ORDER BY id ASC")
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
        return jsonify({"estado": "error", "mensaje": "Nombre e IATA obligatorios"}), 400
    if len(nombre) < 3 or len(nombre) > 50:
        return jsonify({"estado": "error", "mensaje": "El nombre debe tener entre 3 y 50 caracteres"}), 400
    if not REGEX_SOLO_LETRAS.match(nombre):
        return jsonify({"estado": "error", "mensaje": "El nombre no puede tener emojis ni números"}), 400
    if not REGEX_IATA.match(codigo_iata):
        return jsonify({"estado": "error", "mensaje": "El código IATA debe constar de 3 letras"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO origenes (nombre, codigo_iata, activo) VALUES (%s, %s, true) RETURNING id, nombre, codigo_iata, activo",
                (nombre, codigo_iata)
            )
            nuevo = cur.fetchone()
            conn.commit()
            return jsonify({"estado": "exito", "origen": nuevo}), 201
    except Exception:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": "El origen o código IATA ya existe"}), 409
    finally:
        conn.close()

@admin_bp.route("/admin/origenes/<int:origen_id>", methods=["PUT"])
@token_requerido
@admin_requerido
def editar_origen(origen_id):
    datos = request.get_json(silent=True) or {}
    nombre = datos.get("nombre", "").strip()
    codigo_iata = datos.get("codigo_iata", "").strip().upper()
    activo = datos.get("activo", True)

    if not nombre or not codigo_iata:
        return jsonify({"estado": "error", "mensaje": "Nombre e IATA requeridos"}), 400
    if not REGEX_SOLO_LETRAS.match(nombre) or not REGEX_IATA.match(codigo_iata):
        return jsonify({"estado": "error", "mensaje": "Formato de nombre o IATA no válido"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE origenes 
                SET nombre = %s, codigo_iata = %s, activo = %s 
                WHERE id = %s 
                RETURNING id, nombre, codigo_iata, activo
                """,
                (nombre, codigo_iata, activo, origen_id)
            )
            act = cur.fetchone()
            if not act:
                return jsonify({"estado": "error", "mensaje": "Origen no encontrado"}), 404
            conn.commit()
            return jsonify({"estado": "exito", "origen": act}), 200
    finally:
        conn.close()

# SOFT DELETE DE ORIGEN
@admin_bp.route("/admin/origenes/<int:origen_id>", methods=["DELETE"])
@token_requerido
@admin_requerido
def soft_delete_origen(origen_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE origenes SET activo = false WHERE id = %s RETURNING id", (origen_id,))
            if not cur.fetchone():
                return jsonify({"estado": "error", "mensaje": "Origen no encontrado"}), 404
            conn.commit()
            return jsonify({"estado": "exito", "mensaje": "Origen desactivado (borrado lógico)"}), 200
    finally:
        conn.close()

# ==================== VUELOS (CRUD + SOFT DELETE + HORARIOS NOCTURNOS) ====================

def _validar_itinerario(datos):
    origen = str(datos.get("origen", "")).strip()
    destino = str(datos.get("destino", "")).strip()
    fecha_salida_str = str(datos.get("fecha", "")).strip()
    fecha_llegada_str = str(datos.get("fecha_llegada") or fecha_salida_str).strip()
    hora_salida = str(datos.get("hora_salida", "")).strip()[:5]
    hora_llegada = str(datos.get("hora_llegada", "")).strip()[:5]
    precio_raw = datos.get("precio")
    asientos_raw = datos.get("asientos_totales", 40)

    if not all([origen, destino, fecha_salida_str, fecha_llegada_str, hora_salida, hora_llegada, precio_raw]):
        return False, "Todos los campos del itinerario son obligatorios", None

    if origen.lower() == destino.lower():
        return False, "El origen y el destino no pueden ser la misma ciudad", None

    if not REGEX_SOLO_LETRAS.match(origen) or not REGEX_SOLO_LETRAS.match(destino):
        return False, "Las ciudades no deben contener emojis", None

    if not REGEX_HORA.match(hora_salida) or not REGEX_HORA.match(hora_llegada):
        return False, "Formato de hora inválido (HH:MM)", None

    # VALIDACIÓN DE FECHA Y CRUCE DE MEDIANOCHE CON DATETIME COMPLETO
    try:
        dt_salida = datetime.strptime(f"{fecha_salida_str} {hora_salida}", "%Y-%m-%d %H:%M")
        dt_llegada = datetime.strptime(f"{fecha_llegada_str} {hora_llegada}", "%Y-%m-%d %H:%M")
    except ValueError:
        return False, "Formato de fecha o de hora inválido", None

    # La salida no puede ser anterior al día de hoy
    if dt_salida.date() < date.today():
        return False, "La fecha de salida no puede estar en el pasado", None

    # REGLA MAESTRA DE NEGOCIO: Salida estrictamente previa a la llegada
    if dt_salida >= dt_llegada:
        return False, (
            f"Conflicto de itinerario: La salida ({dt_salida.strftime('%d-%b %H:%M')}) "
            f"debe ser previa a la llegada ({dt_llegada.strftime('%d-%b %H:%M')}). "
            "Si el vuelo llega de madrugada, verifique que la 'Fecha Llegada' sea el día siguiente."
        ), None

    try:
        precio = float(precio_raw)
        if precio <= 0 or precio > 10000:
            return False, "El precio debe estar entre \$1.00 y \$10,000.00", None
    except (ValueError, TypeError):
        return False, "El precio debe ser un número válido", None

    try:
        asientos_totales = int(asientos_raw)
        if asientos_totales < 10 or asientos_totales > 350:
            return False, "Los asientos deben estar entre 10 y 350", None
    except (ValueError, TypeError):
        return False, "Los asientos deben ser un número entero", None

    parsed = {
        "origen": origen,
        "destino": destino,
        "fecha": fecha_salida_str,
        "fecha_llegada": fecha_llegada_str,
        "hora_salida": hora_salida,
        "hora_llegada": hora_llegada,
        "precio": round(precio, 2),
        "asientos_totales": asientos_totales,
    }
    return True, "", parsed

@admin_bp.route("/admin/vuelos", methods=["POST"])
@token_requerido
@admin_requerido
def crear_vuelo():
    datos = request.get_json(silent=True) or {}
    valido, mensaje, p = _validar_itinerario(datos)
    if not valido:
        return jsonify({"estado": "error", "mensaje": mensaje}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vuelos (origen, destino, fecha, fecha_llegada, hora_salida, hora_llegada, 
                                   precio, asientos_disponibles, asientos_totales, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                RETURNING id, origen, destino, fecha, fecha_llegada, hora_salida, hora_llegada, 
                          precio, asientos_disponibles, asientos_totales, activo
                """,
                (p["origen"], p["destino"], p["fecha"], p["fecha_llegada"], p["hora_salida"],
                 p["hora_llegada"], p["precio"], p["asientos_totales"], p["asientos_totales"])
            )
            nuevo = cur.fetchone()
            conn.commit()

            nuevo["fecha"] = str(nuevo["fecha"])
            nuevo["fecha_llegada"] = str(nuevo["fecha_llegada"])
            nuevo["hora_salida"] = str(nuevo["hora_salida"])
            nuevo["hora_llegada"] = str(nuevo["hora_llegada"])
            nuevo["precio"] = float(nuevo["precio"])

            return jsonify({"estado": "exito", "vuelo": nuevo}), 201
    finally:
        conn.close()

@admin_bp.route("/admin/vuelos/<int:vuelo_id>", methods=["PUT"])
@token_requerido
@admin_requerido
def editar_vuelo(vuelo_id):
    datos = request.get_json(silent=True) or {}
    valido, mensaje, p = _validar_itinerario(datos)
    if not valido:
        return jsonify({"estado": "error", "mensaje": mensaje}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Obtener datos anteriores para no descuadrar asientos reservados
            cur.execute("SELECT asientos_disponibles, asientos_totales FROM vuelos WHERE id = %s", (vuelo_id,))
            actual = cur.fetchone()
            if not actual:
                return jsonify({"estado": "error", "mensaje": "Vuelo no encontrado"}), 404

            reservados = actual["asientos_totales"] - actual["asientos_disponibles"]
            if p["asientos_totales"] < reservados:
                return jsonify({
                    "estado": "error", 
                    "mensaje": f"No puede reducir la capacidad a {p['asientos_totales']}: ya hay {reservados} asientos reservados."
                }), 400

            nuevos_disponibles = p["asientos_totales"] - reservados

            cur.execute(
                """
                UPDATE vuelos 
                SET origen = %s, destino = %s, fecha = %s, fecha_llegada = %s, hora_salida = %s, 
                    hora_llegada = %s, precio = %s, asientos_disponibles = %s, asientos_totales = %s
                WHERE id = %s
                RETURNING id, origen, destino, fecha, fecha_llegada, hora_salida, hora_llegada, 
                          precio, asientos_disponibles, asientos_totales, activo
                """,
                (p["origen"], p["destino"], p["fecha"], p["fecha_llegada"], p["hora_salida"], 
                 p["hora_llegada"], p["precio"], nuevos_disponibles, p["asientos_totales"], vuelo_id)
            )
            editado = cur.fetchone()
            conn.commit()

            editado["fecha"] = str(editado["fecha"])
            editado["fecha_llegada"] = str(editado["fecha_llegada"])
            editado["hora_salida"] = str(editado["hora_salida"])
            editado["hora_llegada"] = str(editado["hora_llegada"])
            editado["precio"] = float(editado["precio"])

            return jsonify({"estado": "exito", "vuelo": editado}), 200
    finally:
        conn.close()

# SOFT DELETE DE VUELO (Evita violaciones de Foreign Key en reservas históricas)
@admin_bp.route("/admin/vuelos/<int:vuelo_id>", methods=["DELETE"])
@token_requerido
@admin_requerido
def soft_delete_vuelo(vuelo_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE vuelos SET activo = false WHERE id = %s RETURNING id", (vuelo_id,))
            if not cur.fetchone():
                return jsonify({"estado": "error", "mensaje": "Vuelo no encontrado"}), 404
            conn.commit()
            return jsonify({"estado": "exito", "mensaje": "Vuelo desactivado (borrado lógico)"}), 200
    finally:
        conn.close()