from datetime import datetime, date
import xml.etree.ElementTree as ET
from xml.dom import minidom

def _formatear_fecha(valor, formato="%Y-%m-%d"):
    if isinstance(valor, (datetime, date)):
        return valor.strftime(formato)
    return str(valor)

def construir_comprobante_xml(reserva_data: dict) -> str:
    """
    Construye y formatea el árbol XML para el Comprobante SOA 
    garantizando interoperabilidad estándar.
    """
    ticket = ET.Element("ComprobanteReserva")
    
    cabecera = ET.SubElement(ticket, "Cabecera")
    ET.SubElement(cabecera, "Codigo").text = str(reserva_data.get("codigo_reserva", ""))
    ET.SubElement(cabecera, "FechaEmision").text = _formatear_fecha(
        reserva_data.get("fecha_reserva"), "%Y-%m-%d %H:%M:%S"
    )
    ET.SubElement(cabecera, "Estado").text = str(reserva_data.get("estado", "CONFIRMADA")).upper()

    pasajero = ET.SubElement(ticket, "Pasajero")
    ET.SubElement(pasajero, "Nombre").text = str(reserva_data.get("usuario_nombre", ""))
    ET.SubElement(pasajero, "CedulaRUC").text = str(reserva_data.get("cedula_ruc", ""))
    ET.SubElement(pasajero, "Correo").text = str(reserva_data.get("correo", ""))
# Reemplaza la sección 3 de construir_comprobante_xml:
    # 3. Detalle del Vuelo Reservado
    vuelo = ET.SubElement(ticket, "DetalleVuelo")
    ET.SubElement(vuelo, "Ruta").text = f"{reserva_data.get('origen')} -> {reserva_data.get('destino')}"
    ET.SubElement(vuelo, "FechaVuelo").text = _formatear_fecha(reserva_data.get("fecha"), "%Y-%m-%d")
    ET.SubElement(vuelo, "HoraSalida").text = str(reserva_data.get("hora_salida", ""))
    ET.SubElement(vuelo, "AsientosReservados").text = str(reserva_data.get("cantidad_asientos", 1))
    ET.SubElement(vuelo, "AsientosAsignados").text = str(reserva_data.get("asientos", "N/A"))
    ET.SubElement(vuelo, "PrecioUnitario").text = f"{float(reserva_data.get('precio', 0.0)):.2f}"

    totales = ET.SubElement(ticket, "Totales")
    ET.SubElement(totales, "Subtotal").text = f"{float(reserva_data.get('subtotal', 0.0)):.2f}"
    ET.SubElement(totales, "IVA").text = f"{float(reserva_data.get('iva', 0.0)):.2f}"
    ET.SubElement(totales, "TotalPagar").text = f"{float(reserva_data.get('total', 0.0)):.2f}"

    xml_crudo = ET.tostring(ticket, encoding="utf-8")
    return minidom.parseString(xml_crudo).toprettyxml(indent="  ")