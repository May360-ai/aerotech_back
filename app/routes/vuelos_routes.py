from flask import Blueprint, jsonify
from database import get_db_connection

vuelos_bp = Blueprint("vuelos_bp", __name__)

@vuelos_bp.route("/vuelos", methods=["GET"])
def listar_vuelos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM vuelos WHERE asientos_disponibles > 0 ORDER BY fecha ASC")
            vuelos = cur.fetchall()
            for v in vuelos:
                v["fecha"] = v["fecha"].strftime("%Y-%m-%d")
                v["hora_salida"] = str(v["hora_salida"])
                v["hora_llegada"] = str(v["hora_llegada"])
                v["precio"] = float(v["precio"])
            return jsonify(vuelos), 200
    finally:
        conn.close()