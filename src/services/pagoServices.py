import mercadopago
from asyncpg import Connection
from fastapi import HTTPException, status

from core.config import settings
from utils.exceptions import NotFoundException, DatabaseException
from schemas.pagoSchema import PreferenciaPagoResponse

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime

# Inicializamos el SDK de MercadoPago con tu Token
token_value = settings.MP_ACCESS_TOKEN.get_secret_value()
sdk = mercadopago.SDK(token_value)

# -------------------------
# Crear preferencia de pago
# -------------------------
async def crear_preferencia_pago(conn: Connection, id_cuota: int) -> PreferenciaPagoResponse:
    """
    Genera una preferencia de pago en MercadoPago para una cuota específica.
    """
    try:
        # --- DEBUG TOKEN ---
        # Imprimimos los primeros caracteres del token para verificar cuál estás usando
        prefix = token_value[:10] if token_value else "NONE"
        print(f"\n[DEBUG] Usando Token que empieza con: {prefix}...")
        # -------------------

        # 1. Buscar la cuota en la BD
        query = """
            SELECT 
                c."idCuota", 
                c.monto, 
                c.mes, 
                c."nombreTrabajo",
                p.dni,
                p.email,
                p.nombre,
                p.apellido
            FROM "Cuota" c
            JOIN "Persona" p ON c.dni = p.dni
            WHERE c."idCuota" = $1
        """
        cuota = await conn.fetchrow(query, id_cuota)
        
        if not cuota:
            raise NotFoundException("Cuota", id_cuota)

        # 2. Configurar los datos de la preferencia
        mi_url_ngrok = settings.URL_NGROK 
        
        preference_data = {
            "items": [
                {
                    "id": str(cuota["idCuota"]),
                    "title": f"Cuota {cuota['mes']} - {cuota['nombreTrabajo']}",
                    "quantity": 1,
                    "unit_price": float(cuota["monto"]),
                    "currency_id": "ARS"
                }
            ],
            # Datos del pagador (Opcional, pero recomendado si tienes los datos del alumno)
            "payer": { 
                "email": cuota["email"],
                "name": cuota["nombre"],
                "surname": cuota["apellido"],
                "identification": {
                    "type": "DNI",
                    "number": cuota["dni"]
                }
            },
            
            # Referencia externa: Vital para saber qué cuota se pagó cuando vuelva el webhook
            "external_reference": str(cuota["idCuota"]),

            "back_urls": {
                "success": f"{mi_url_ngrok}/pagos/retorno",
                "failure": f"{mi_url_ngrok}/pagos/retorno",
                "pending": f"{mi_url_ngrok}/pagos/retorno"
            },
            "auto_return": "approved",
            
            # Aquí es donde MP notificará el pago a tu Backend (vía Ngrok)
            "notification_url": f"{mi_url_ngrok}/pagos/webhook",

            # Opcional: Esto hace que no puedan cambiar el email en el checkout
            "binary_mode": True
        }

        # --- DEBUG PREFERENCIA ---
        print("\n--- DEBUG: ENVIANDO PREFERENCIA A MP ---")
        print(preference_data)
        print("----------------------------------------\n")

        # 3. Crear la preferencia en la API de MercadoPago
        preference_response = sdk.preference().create(preference_data)
        
        # --- DEBUG RESPUESTA ---
        print("--- DEBUG: RESPUESTA DE MP ---")
        print(f"Status: {preference_response.get('status')}")
        # Verificamos si hay sandbox_init_point en la respuesta cruda
        raw_response = preference_response.get("response", {})
        print(f"Sandbox Init Point: {raw_response.get('sandbox_init_point')}")
        print("------------------------------\n")
        # -----------------------

        if preference_response["status"] != 201:
            print(f"ERROR MP DETALLE: {preference_response}") # Ver error completo si falla
            raise Exception(f"Error al crear preferencia en MP: {preference_response}")

        response_data = preference_response["response"]

        return PreferenciaPagoResponse(
            init_point=response_data["init_point"], 
            sandbox_init_point=response_data["sandbox_init_point"] 
        )

    except NotFoundException:
        raise
    except Exception as e:
        print(f"Error creando preferencia: {e}")
        raise DatabaseException("iniciar pago", str(e))

# -------------------------
# Webhook
# -------------------------
async def procesar_pago_exitoso(conn: Connection, payment_id: str) -> bool:
    """
    1. Consulta a MercadoPago el estado real del pago usando su ID.
    2. Si está aprobado ('approved'), marca la cuota como pagada en la BD.
    """
    try:
        # 1. Consultar a MercadoPago (Fuente de la verdad)
        payment_info = sdk.payment().get(payment_id)
        
        if payment_info["status"] != 200:
            print(f"⚠️ No se pudo obtener el pago {payment_id} de MP")
            return False
            
        payment_data = payment_info["response"]
        estado = payment_data.get("status")
        id_cuota_str = payment_data.get("external_reference")

        print(f"🔔 Webhook recibido: Pago {payment_id} para Cuota {id_cuota_str} - Estado: {estado}")

        # 2. Si el pago está aprobado, actualizamos la base de datos
        if estado == "approved" and id_cuota_str:
            id_cuota = int(id_cuota_str)
            
            # Actualizar la cuota a pagada=True
            query = '''
                UPDATE "Cuota" 
                SET pagada = TRUE, 
                    "fechaDePago" = CURRENT_DATE, 
                    "horaDePago" = CURRENT_TIME(0)
                WHERE "idCuota" = $1
            '''
            result = await conn.execute(query, id_cuota)
            
            if result == "UPDATE 1":
                print(f"✅ Cuota {id_cuota} marcada como PAGADA exitosamente.")
                return True
            else:
                print(f"❌ Error: La cuota {id_cuota} no se encontró o no se pudo actualizar.")
        
        return False

    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        raise DatabaseException("procesar webhook", str(e))

async def obtener_estado_pago_cuota(conn: Connection, id_cuota: int) -> bool:
    """Retorna True si la cuota está pagada, False si no."""
    query = 'SELECT pagada FROM "Cuota" WHERE "idCuota" = $1'
    pagada = await conn.fetchval(query, id_cuota)
    if pagada is None:
        raise NotFoundException("Cuota", id_cuota)
    return pagada

# -------------------------
# Generar comprobante de pago PDF
# -------------------------
async def generar_comprobante_pdf(conn: Connection, id_cuota: int):
    """
    Genera un archivo PDF en memoria con los datos del comprobante.
    """
    # 1. Obtener datos completos de la cuota y el alumno
    query = """
        SELECT 
            c."idCuota", c.monto, c.mes, c."nombreTrabajo", c."nombreSuscripcion",
            c."fechaDePago", c."horaDePago",
            p.nombre, p.apellido, p.dni, p.email
        FROM "Cuota" c
        JOIN "Persona" p ON c.dni = p.dni
        WHERE c."idCuota" = $1 AND c.pagada = TRUE
    """
    row = await conn.fetchrow(query, id_cuota)

    if not row:
        raise NotFoundException("Comprobante no disponible (Cuota no pagada o inexistente)", id_cuota)

    # 2. Crear el PDF en memoria
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- DISEÑO DEL COMPROBANTE ---
    
    # Encabezado
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2 * cm, height - 3 * cm, "GIMNASIO ABITO")
    
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 4 * cm, "Comprobante de Pago")
    c.drawString(2 * cm, height - 4.5 * cm, f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Datos del Alumno
    c.line(2 * cm, height - 5 * cm, width - 2 * cm, height - 5 * cm)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, height - 6 * cm, "Datos del Alumno")
    
    c.setFont("Helvetica", 11)
    y = height - 7 * cm
    c.drawString(2.5 * cm, y, f"Nombre: {row['nombre']} {row['apellido']}")
    c.drawString(2.5 * cm, y - 15, f"DNI: {row['dni']}")
    c.drawString(2.5 * cm, y - 30, f"Email: {row['email']}")

    # Detalle del Pago
    c.line(2 * cm, y - 50, width - 2 * cm, y - 50)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y - 70, "Detalle del Pago")

    y_detalle = y - 90
    c.setFont("Helvetica", 11)
    
    # Formatear fecha y hora de pago si existen
    fecha_pago = row['fechaDePago'].strftime('%d/%m/%Y') if row['fechaDePago'] else "-"
    hora_pago = row['horaDePago'].strftime('%H:%M') if row['horaDePago'] else "-"

    c.drawString(2.5 * cm, y_detalle, f"Concepto: Cuota {row['mes']} - {row['nombreTrabajo']}")
    c.drawString(2.5 * cm, y_detalle - 15, f"Plan: {row['nombreSuscripcion']}")
    c.drawString(2.5 * cm, y_detalle - 30, f"Fecha de Pago: {fecha_pago} a las {hora_pago} hs")
    c.drawString(2.5 * cm, y_detalle - 45, f"ID Transacción: #{row['idCuota']}")

    # Total
    c.setFont("Helvetica-Bold", 16)
    c.drawString(12 * cm, y_detalle - 80, f"TOTAL: ${row['monto']:,.2f}")

    # Pie de página
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, 2 * cm, "Gracias por confiar en Gimnasio Abito")

    c.save()
    buffer.seek(0)
    return buffer


