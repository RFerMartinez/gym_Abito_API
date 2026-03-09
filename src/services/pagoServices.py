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
from datetime import datetime, date

# Inicializamos el SDK de MercadoPago con tu Token
# token_value = settings.MP_ACCESS_TOKEN.get_secret_value()
# sdk = mercadopago.SDK(token_value)

def obtener_sdk(cuenta: str = "mia") -> mercadopago.SDK:
    """Devuelve una instancia del SDK según la cuenta solicitada."""
    if cuenta == "davor":
        return mercadopago.SDK(settings.MP_ACCESS_TOKEN_DAVOR.get_secret_value())
    return mercadopago.SDK(settings.MP_ACCESS_TOKEN.get_secret_value())

async def obtener_turno_pago(conn: Connection, id_cuota: int) -> str:
    """
    Determina si el pago es para 'mañana' o 'tarde' basado en el 
    primer grupo asignado al alumno de la cuota.
    """
    query = """
        SELECT 
            CASE
                WHEN LEFT(MIN(asis."nroGrupo"), 1) IN ('1', '2') THEN 'mañana'
                WHEN LEFT(MIN(asis."nroGrupo"), 1) IN ('3', '4', '5') THEN 'tarde'
                ELSE 'mañana'
            END as turno
        FROM "Asiste" asis
        JOIN "Cuota" c ON asis.dni = c.dni
        WHERE c."idCuota" = $1
    """
    turno = await conn.fetchval(query, id_cuota)
    return turno or "mañana"

# -------------------------
# Crear preferencia de pago
# -------------------------
async def crear_preferencia_pago(conn: Connection, id_cuota: int, monto_final: float) -> PreferenciaPagoResponse:
    """
    Genera una preferencia de pago en MercadoPago usando el monto provisto.
    """
    try:
        # 1. Buscar datos y determinar turno
        turno = await obtener_turno_pago(conn, id_cuota)
        cuenta_destino = "davor" if turno == "tarde" else "mia"
        sdk = obtener_sdk(cuenta_destino)

        # Buscar datos descriptivos (mantener tu query actual)
        query = 'SELECT c."idCuota", c.mes, c."nombreTrabajo", p.dni, p.email, p.nombre, p.apellido FROM "Cuota" c JOIN "Persona" p ON c.dni = p.dni WHERE c."idCuota" = $1'
        cuota = await conn.fetchrow(query, id_cuota)
        if not cuota: raise NotFoundException("Cuota", id_cuota)

        # 2. Configurar MercadoPago
        mi_url_ngrok = settings.URL_NGROK 
        
        preference_data = {
            "items": [{"id": str(cuota["idCuota"]), "title": f"Cuota {cuota['mes']} - {cuota['nombreTrabajo']}", "quantity": 1, "unit_price": float(monto_final), "currency_id": "ARS"}],
            "payer": {"email": cuota["email"], "name": cuota["nombre"], "surname": cuota["apellido"], "identification": {"type": "DNI", "number": cuota["dni"]}},
            "external_reference": str(cuota["idCuota"]),
            "back_urls": {
                "success": f"{mi_url_ngrok}/pagos/retorno",
                "failure": f"{mi_url_ngrok}/pagos/retorno",
                "pending": f"{mi_url_ngrok}/pagos/retorno"
            },
            "auto_return": "approved",
            # AGREGAMOS ?owner=... para que el webhook sepa qué token usar al verificar
            "notification_url": f"{mi_url_ngrok}/pagos/webhook?owner={cuenta_destino}",
            "binary_mode": True
        }

        preference_response = sdk.preference().create(preference_data)
        
        if preference_response["status"] != 201:
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
async def procesar_pago_exitoso(conn: Connection, payment_id: str, owner: str = "mia") -> bool:
    try:
        # ... (código inicial para obtener SDK y payment_info igual que antes) ...
        sdk = obtener_sdk(owner)
        payment_info = sdk.payment().get(payment_id)
        
        if payment_info["status"] != 200:
            print(f"⚠️ No se pudo obtener el pago {payment_id} de MP")
            return False
            
        payment_data = payment_info["response"]
        estado = payment_data.get("status")
        id_cuota_str = payment_data.get("external_reference")
        monto_pagado_mp = payment_data.get("transaction_amount") 

        print(f"🔔 Webhook: Pago {payment_id} para Cuota {id_cuota_str} - Estado: {estado} - Monto MP: {monto_pagado_mp}")

        if estado == "approved" and id_cuota_str:
            id_cuota = int(id_cuota_str)
            
            # --- CORRECCIÓN DE IDEMPOTENCIA ---
            # Agregamos "AND pagada = FALSE" al final.
            # Esto evita que si MP manda el aviso 2 veces, se aplique el recargo 2 veces.
            query = '''
                UPDATE "Cuota" 
                SET pagada = TRUE, 
                    "fechaDePago" = CURRENT_DATE, 
                    "horaDePago" = CURRENT_TIME(0),
                    "metodoDePago" = 'qr',
                    monto = CASE 
                                WHEN "fechaFin" < CURRENT_DATE THEN ROUND(monto * 1.10, 2)
                                ELSE monto 
                            END
                WHERE "idCuota" = $1 AND pagada = FALSE 
            '''
            
            result = await conn.execute(query, id_cuota)
            
            if result == "UPDATE 1":
                print(f"✅ Cuota {id_cuota} pagada. Base de datos actualizada correctamente.")
                return True
            else:
                # Si el UPDATE no afectó ninguna fila, verificamos por qué
                # Puede ser que no exista O que ya estuviera pagada (por el primer webhook)
                chequeo = await conn.fetchrow('SELECT pagada FROM "Cuota" WHERE "idCuota" = $1', id_cuota)
                
                if chequeo and chequeo['pagada']:
                    print(f"ℹ️ Webhook duplicado: La cuota {id_cuota} ya estaba registrada como pagada. No se realizan cambios.")
                    return True # Retornamos True porque el estado final es correcto (Pagada)
                else:
                    print(f"❌ Error: La cuota {id_cuota} no se encontró.")
                    return False
        
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

async def marcar_pago_manual(conn: Connection, id_cuota: int, metodo_pago: str) -> bool:
    """
    Marca una cuota como pagada manualmente.
    Si la cuota está vencida (fechaFin < HOY), aplica un 10% de recargo al monto automáticamente.
    """
    try:
        # Consulta SQL inteligente:
        # 1. Actualiza el estado a pagado y registra fecha/hora/metodo.
        # 2. En la columna 'monto', verifica si la fechaFin es menor a la fecha actual (CURRENT_DATE).
        # 3. Si es menor (vencida), multiplica el monto actual por 1.10. Si no, deja el monto igual.
        query = """
            UPDATE "Cuota"
            SET 
                pagada = TRUE,
                "fechaDePago" = CURRENT_DATE,
                "horaDePago" = CURRENT_TIME,
                "metodoDePago" = $2,
                monto = CASE 
                            WHEN "fechaFin" < CURRENT_DATE THEN ROUND(monto * 1.10, 2)
                            ELSE monto 
                        END
            WHERE "idCuota" = $1
            RETURNING "idCuota"; 
        """
        
        # Usamos fetchval para verificar si devolvió un ID (significa que encontró y actualizó la fila)
        result_id = await conn.fetchval(query, id_cuota, metodo_pago)
        
        if not result_id:
            raise NotFoundException("Cuota", id_cuota)

        return True

    except Exception as e:
        print(f"Error en marcar_pago_manual: {e}")
        raise DatabaseException("marcar pago manual", str(e))


