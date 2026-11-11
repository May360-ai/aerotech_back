from datetime import datetime, date
from flask import Blueprint, jsonify
from database import get_db_connection

vuelos_bp = Blueprint("vuelos_bp", __name__)

@vuelos_bp.route("/vuelos", methods=["GET"])
def listar_vuelos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, origen, destino, fecha, hora_salida, hora_llegada, 
                       precio, asientos_disponibles 
                FROM vuelos 
                WHERE asientos_disponibles > 0 
                ORDER BY fecha ASC, hora_salida ASC
                """
            )
            vuelos = cur.fetchall()

            for v in vuelos:
                if isinstance(v["fecha"], (datetime, date)):
                    v["fecha"] = v["fecha"].strftime("%Y-%m-%d")
                else:
                    v["fecha"] = str(v["fecha"])
                v["hora_salida"] = str(v["hora_salida"])
                v["hora_llegada"] = str(v["hora_llegada"])
                v["precio"] = float(v["precio"])

            return jsonify(vuelos), 200
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": f"Error al consultar vuelos: {str(e)}"}), 500
    finally:
        conn.close()

@vuelos_bp.route("/vuelos/<int:vuelo_id>/asientos-ocupados", methods=["GET"])
def obtener_asientos_ocupados(vuelo_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT asientos 
                FROM reservas 
                WHERE vuelo_id = %s AND estado != 'cancelada' AND asientos IS NOT NULL
                """,
                (vuelo_id,)
            )
            reservas = cur.fetchall()

            asientos_ocupados = []
            for r in reservas:
                if r.get("asientos"):
                    items = [a.strip() for a in r["asientos"].split(",") if a.strip()]
                    asientos_ocupados.extend(items)

            return jsonify({"asientos_ocupados": asientos_ocupados}), 200
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500
    finally:
        conn.close()