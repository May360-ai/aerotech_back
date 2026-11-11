from datetime import datetime, date
from flask import Blueprint, request, jsonify, Response
from database import get_db_connection
from app.middlewares.auth import token_requerido
from app.utils.xml_helper import construir_comprobante_xml
from config import Config

reservas_bp = Blueprint("reservas_bp", __name__)

@reservas_bp.route("/reservas", methods=["POST"])
@token_requerido
def crear_reserva():
    datos = request.get_json(silent=True) or {}
    vuelo_id = datos.get("vuelo_id")
    asientos_solicitados = datos.get("asientos", [])

    if isinstance(asientos_solicitados, list) and len(asientos_solicitados) > 0:
        cantidad = len(asientos_solicitados)
    else:
        try:
            cantidad = int(datos.get("cantidad", 1))
        except (ValueError, TypeError):
            cantidad = 1

    if cantidad <= 0:
        return jsonify({"estado": "error", "mensaje": "Debe seleccionar al menos un asiento"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vuelos WHERE id = %s FOR UPDATE", (vuelo_id,))
            vuelo = cur.fetchone()

            if not vuelo:
                return jsonify({"estado": "error", "mensaje": "El vuelo seleccionado no existe"}), 404

            if vuelo["asientos_disponibles"] < cantidad:
                return jsonify({
                    "estado": "error",
                    "mensaje": f"Solo quedan {vuelo['asientos_disponibles']} asientos disponibles."
                }), 409

            if asientos_solicitados:
                cur.execute(
                    """
                    SELECT asientos FROM reservas 
                    WHERE vuelo_id = %s AND estado != 'cancelada' AND asientos IS NOT NULL
                    """,
                    (vuelo_id,)
                )
                reservas_existentes = cur.fetchall()
                ya_ocupados = set()
                for r in reservas_existentes:
                    if r.get("asientos"):
                        ya_ocupados.update([a.strip() for a in r["asientos"].split(",") if a.strip()])

                colisiones = [a for a in asientos_solicitados if a in ya_ocupados]
                if colisiones:
                    conn.rollback()
                    return jsonify({
                        "estado": "error",
                        "mensaje": f"El/los asiento(s) {', '.join(colisiones)} acaban de ser reservados por otro usuario."
                    }), 409

            cur.execute(
                """
                UPDATE vuelos 
                SET asientos_disponibles = asientos_disponibles - %s 
                WHERE id = %s AND asientos_disponibles >= %s
                """,
                (cantidad, vuelo_id, cantidad)
            )

            precio_unitario = float(vuelo["precio"])
            subtotal = round(precio_unitario * cantidad, 2)
            iva = round(subtotal * Config.IVA_PORCENTAJE, 2)
            total = round(subtotal + iva, 2)
            codigo = f"TICK-{int(datetime.now().timestamp())}"
            cadena_asientos = ", ".join(asientos_solicitados) if asientos_solicitados else f"{cantidad} Asiento(s)"

            cur.execute(
                """
                INSERT INTO reservas (codigo_reserva, usuario_id, vuelo_id, cantidad_asientos, subtotal, iva, total, estado, asientos)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'confirmada', %s)
                RETURNING id, codigo_reserva, subtotal, iva, total, estado, asientos
                """,
                (codigo, request.user_id, vuelo_id, cantidad, subtotal, iva, total, cadena_asientos)
            )
            reserva = cur.fetchone()
            conn.commit()

            return jsonify({
                "estado": "exito",
                "mensaje": "Reserva creada con éxito",
                "reserva_id": reserva["id"],
                "total": total,
                "reserva": reserva
            }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"estado": "error", "mensaje": f"Error interno: {str(e)}"}), 500
    finally:
        conn.close()

@reservas_bp.route("/reservas/<int:reserva_id>", methods=["GET"])
@token_requerido
def obtener_reserva(reserva_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.*, u.nombre AS usuario_nombre, u.cedula_ruc, u.correo,
                       v.origen, v.destino, v.fecha, v.hora_salida, v.precio
                FROM reservas r
                JOIN usuarios u ON r.usuario_id = u.id
                JOIN vuelos v ON r.vuelo_id = v.id
                WHERE r.id = %s
                """,
                (reserva_id,)
            )
            r = cur.fetchone()
            if not r:
                return jsonify({"estado": "error", "mensaje": "Reserva no encontrada"}), 404

            if isinstance(r["fecha"], (datetime, date)):
                r["fecha"] = r["fecha"].strftime("%Y-%m-%d")
            if isinstance(r["fecha_reserva"], (datetime, date)):
                r["fecha_reserva"] = r["fecha_reserva"].strftime("%Y-%m-%d %H:%M:%S")

            r["hora_salida"] = str(r["hora_salida"])
            r["precio"] = float(r["precio"])
            r["subtotal"] = float(r["subtotal"])
            r["iva"] = float(r["iva"])
            r["total"] = float(r["total"])

            return jsonify(r), 200
    finally:
        conn.close()

@reservas_bp.route("/reservas/<int:reserva_id>/comprobante-xml", methods=["GET"])
@token_requerido
def generar_comprobante_xml(reserva_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.*, u.nombre AS usuario_nombre, u.cedula_ruc, u.correo,
                       v.origen, v.destino, v.fecha, v.hora_salida, v.precio
                FROM reservas r
                JOIN usuarios u ON r.usuario_id = u.id
                JOIN vuelos v ON r.vuelo_id = v.id
                WHERE r.id = %s
                """,
                (reserva_id,)
            )
            r = cur.fetchone()
            if not r:
                return jsonify({"estado": "error", "mensaje": "Reserva no encontrada"}), 404

            xml_salida = construir_comprobante_xml(r)
            return Response(xml_salida, mimetype="application/xml")
    finally:
        conn.close()