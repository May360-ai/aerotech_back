import xml.etree.ElementTree as ET
from xml.dom import minidom

def construir_comprobante_xml(reserva_data: dict) -> str:
    """Construye y formatea el árbol XML para el comprobante de reserva."""
    ticket = ET.Element("ComprobanteReserva")
    
    # Cabecera
    cabecera = ET.SubElement(ticket, "Cabecera")
    ET.SubElement(cabecera, "Codigo").text = reserva_data["codigo_reserva"]
    ET.SubElement(cabecera, "FechaEmision").text = reserva_data["fecha_reserva"].strftime("%Y-%m-%d %H:%M:%S")
    ET.SubElement(cabecera, "Estado").text = reserva_data["estado"].upper()

    # Datos del Pasajero
    pasajero = ET.SubElement(ticket, "Pasajero")
    ET.SubElement(pasajero, "Nombre").text = reserva_data["usuario_nombre"]
    ET.SubElement(pasajero, "CedulaRUC").text = reserva_data["cedula_ruc"]
    ET.SubElement(pasajero, "Correo").text = reserva_data["correo"]

    # Detalle del Vuelo
    vuelo = ET.SubElement(ticket, "DetalleVuelo")
    ET.SubElement(vuelo, "Ruta").text = f"{reserva_data['origen']} -> {reserva_data['destino']}"
    ET.SubElement(vuelo, "FechaVuelo").text = reserva_data["fecha"].strftime("%Y-%m-%d")
    ET.SubElement(vuelo, "HoraSalida").text = str(reserva_data["hora_salida"])
    ET.SubElement(vuelo, "AsientosReservados").text = str(reserva_data["cantidad_asientos"])
    ET.SubElement(vuelo, "PrecioUnitario").text = f"{float(reserva_data['precio']):.2f}"

    # Totales
    totales = ET.SubElement(ticket, "Totales")
    ET.SubElement(totales, "Subtotal").text = f"{float(reserva_data['subtotal']):.2f}"
    ET.SubElement(totales, "IVA").text = f"{float(reserva_data['iva']):.2f}"
    ET.SubElement(totales, "TotalPagar").text = f"{float(reserva_data['total']):.2f}"

    xml_crudo = ET.tostring(ticket, encoding="utf-8")
    return minidom.parseString(xml_crudo).toprettyxml(indent="  ")