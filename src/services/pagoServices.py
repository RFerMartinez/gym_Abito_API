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
from reportlab.lib import colors

# Inicializamos el SDK de MercadoPago con tu Token
# token_value = settings.MP_ACCESS_TOKEN.get_secret_value()
# sdk = mercadopago.SDK(token_value)

def obtener_sdk(cuenta: str = "administrador") -> mercadopago.SDK:
    """
    Devuelve la instancia del SDK de MercadoPago según el titular de la cuenta.
    - 'empleado': Usa el token MP_ACCESS_TOKEN_EMP
    - 'administrador': Usa el token MP_ACCESS_TOKEN_ADM
    """
    if cuenta == "empleado":
        return mercadopago.SDK(settings.MP_ACCESS_TOKEN_EMP.get_secret_value())
    
    # Por defecto usamos la cuenta del administrador
    return mercadopago.SDK(settings.MP_ACCESS_TOKEN_ADM.get_secret_value())



# -------------------------
# Crear preferencia de pago
# -------------------------
async def crear_preferencia_pago(conn: Connection, id_cuota: int, monto_final: float) -> PreferenciaPagoResponse:
    """
    Genera una preferencia de pago en MercadoPago.
    Decide la cuenta destino (Admin o Empleado) basándose en el campo 'titular' de la cuota.
    """
    try:
        # A. Buscar datos completos de la cuota y el alumno
        query = """
            SELECT 
                c."idCuota", 
                c.mes, 
                c."nombreTrabajo", 
                c.titular,  -- Campo clave para decidir el destino del dinero
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

        # B. Determinar la cuenta destino
        titular_cuota = cuota["titular"]
        
        # Si el titular es 'Administración' (o nulo por compatibilidad), va a la cuenta del Admin.
        # Si tiene cualquier otro nombre (es un empleado), va a la cuenta del Empleado.
        if titular_cuota == "Administración" or titular_cuota is None:
            cuenta_destino = "administrador"
        else:
            cuenta_destino = "empleado"
            
        sdk = obtener_sdk(cuenta_destino)

        # C. Configurar Preferencia
        mi_url_back = settings.BACKEND_URL
        mi_url_front = settings.FRONTEND_URL
        
        preference_data = {
            "items": [
                {
                    "id": str(cuota["idCuota"]), 
                    "title": f"Cuota {cuota['mes']} - {cuota['nombreTrabajo']}", 
                    "quantity": 1, 
                    "unit_price": float(monto_final), 
                    "currency_id": "ARS"
                }
            ],
            "payer": {
                "email": cuota["email"], 
                "name": cuota["nombre"], 
                "surname": cuota["apellido"], 
                "identification": {"type": "DNI", "number": cuota["dni"]}
            },
            "external_reference": str(cuota["idCuota"]),
            "back_urls": {
                "success": f"{mi_url_front}/pagos/retorno",
                "failure": f"{mi_url_front}/pagos/retorno",
                "pending": f"{mi_url_front}/pagos/retorno"
            },
            "auto_return": "approved",
            # IMPORTANTE: Pasamos el 'owner' correcto al webhook para que sepa qué token usar al validar
            "notification_url": f"{mi_url_back}/pagos/webhook?owner={cuenta_destino}",
            "binary_mode": True
        }

        preference_response = sdk.preference().create(preference_data)
        
        if preference_response["status"] != 201:
            raise Exception(f"Error MP: {preference_response}")

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
async def procesar_pago_exitoso(conn: Connection, payment_id: str, owner: str = "administrador") -> bool:
    """
    Verifica y procesa un pago notificado por MercadoPago.
    El parámetro 'owner' ahora espera 'administrador' o 'empleado'.
    """
    try:
        # Seleccionamos el SDK correcto según el parámetro que viene en la URL del webhook
        sdk = obtener_sdk(owner)
        
        payment_info = sdk.payment().get(payment_id)
        
        if payment_info["status"] != 200:
            print(f"No se pudo obtener el pago {payment_id} de MP usando la cuenta: {owner}")
            return False
            
        payment_data = payment_info["response"]
        estado = payment_data.get("status")
        id_cuota_str = payment_data.get("external_reference")
        monto_pagado_mp = payment_data.get("transaction_amount") 

        print(f"Webhook ({owner}): Pago {payment_id} para Cuota {id_cuota_str} - Estado: {estado}")

        if estado == "approved" and id_cuota_str:
            id_cuota = int(id_cuota_str)
            
            # Actualización idempotente (verifica que no esté pagada previamente)
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
                print(f"Cuota {id_cuota} pagada exitosamente.")
                return True
            else:
                # Verificamos si ya estaba pagada
                chequeo = await conn.fetchrow('SELECT pagada FROM "Cuota" WHERE "idCuota" = $1', id_cuota)
                if chequeo and chequeo['pagada']:
                    print(f"ℹ Webhook duplicado: La cuota {id_cuota} ya estaba pagada.")
                    return True
                else:
                    print(f"Error: La cuota {id_cuota} no se encontró.")
                    return False
        
        return False

    except Exception as e:
        print(f"Error procesando webhook: {e}")
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
    Genera un comprobante de pago con diseño premium y marca de seguridad.
    """
    query = """
        SELECT 
            c."idCuota", c.monto, c.mes, c."nombreTrabajo", c."nombreSuscripcion",
            c."fechaDePago", c."horaDePago", c."metodoDePago",
            p.nombre, p.apellido, p.dni, p.email
        FROM "Cuota" c
        JOIN "Persona" p ON c.dni = p.dni
        WHERE c."idCuota" = $1 AND c.pagada = TRUE
    """
    row = await conn.fetchrow(query, id_cuota)

    if not row:
        return None

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    # METADATOS VITALES:
    c.setTitle(f"Comprobante de Pago - {row['nombre']} {row['apellido']}")
    c.setAuthor("Gimnasio Abito")
    c.setSubject(f"Cuota ID: {id_cuota}")
    width, height = A4

    # --- 1. MARCA DE AGUA (GRANDE Y DISTRIBUIDA) ---
    c.saveState()
    c.setFillColorRGB(0.96, 0.96, 0.96) 
    c.setFont("Helvetica-Bold", 110) 
    c.translate(width/2, height/2)
    c.rotate(35)
    
    for x in range(-3, 4):
        for y in range(-5, 6):
            c.drawCentredString(x*700, y*280, "GYM ABITO")
    c.restoreState()

    # --- 2. ENCABEZADO ---
    c.setFillColorRGB(0.89, 0.04, 0.08) # Rojo Abito
    c.rect(0, height - 4*cm, 1.2*cm, 3*cm, fill=1, stroke=0)
    
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(2*cm, height - 2.5*cm, "GIMNASIO")
    
    c.setFillColorRGB(0.89, 0.04, 0.08)
    c.drawString(7.2*cm, height - 2.5*cm, "ABITO") 
    
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(2*cm, height - 3.2*cm, "COMPROBANTE DE PAGO") 
    
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 2*cm, height - 2.5*cm, f"Emitido: {datetime.now().strftime('%d/%m/%Y')}")

    # --- 3. TARJETA DE INFORMACIÓN DEL ALUMNO ---
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.setFillColorRGB(0.98, 0.98, 0.98)
    c.roundRect(1.8*cm, height - 7.5*cm, width - 3.6*cm, 3*cm, 15, stroke=1, fill=1)
    
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5*cm, height - 5.5*cm, "TITULAR DEL PAGO")
    
    c.setFont("Helvetica", 11)
    c.drawString(2.5*cm, height - 6.2*cm, f"{row['nombre'].upper()} {row['apellido'].upper()}")
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(2.5*cm, height - 6.8*cm, f"DNI: {row['dni']}  |  {row['email']}")

    # --- 4. DETALLES DE TRANSACCIÓN ---
    y_detalle = height - 9.5*cm
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y_detalle, "DETALLE DE TRANSACCIÓN")
    
    c.setStrokeColorRGB(0.89, 0.04, 0.08)
    c.setLineWidth(2)
    c.line(2*cm, y_detalle - 0.2*cm, 4*cm, y_detalle - 0.2*cm)

    fecha_p = row['fechaDePago'].strftime('%d/%m/%Y') if row['fechaDePago'] else "-"
    hora_p = row['horaDePago'].strftime('%H:%M') if row['horaDePago'] else "-"

    c.setLineWidth(1)
    c.setStrokeColorRGB(0.92, 0.92, 0.92)
    y_pos = y_detalle - 1.5*cm
    
    items = [
        ("SERVICIO", f"{row['nombreTrabajo']} - {row['nombreSuscripcion']}"),
        ("PERIODO", f"Cuota de {row['mes']}"),
        ("FECHA DE PAGO", f"{fecha_p} a las {hora_p} hs"),
        ("MÉTODO DE PAGO", row['metodoDePago'].upper() if row['metodoDePago'] else "TRANSFERENCIA / QR"),
        ("ID TRANSACCIÓN", f"#{row['idCuota']}")
    ]

    for label, val in items:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(2.5*cm, y_pos, label)
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0.15, 0.15, 0.15)
        c.drawRightString(width - 2.5*cm, y_pos, str(val))
        c.line(2.5*cm, y_pos - 0.3*cm, width - 2.5*cm, y_pos - 0.3*cm)
        y_pos -= 1*cm

    # --- 5. TOTAL (AJUSTE FINAL DE POSICIÓN) ---
    y_total = y_pos - 1.0*cm
    c.setStrokeColorRGB(0.89, 0.04, 0.08)
    c.setLineWidth(2.5)
    
    # La línea ahora es más larga para dar soporte visual a ambos textos separados
    c.line(2.5*cm, y_total + 1.2*cm, width - 2*cm, y_total + 1.2*cm)
    
    # ETIQUETA: Alineada a la IZQUIERDA (2.5cm)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2.5*cm, y_total + 0.4*cm, "TOTAL ABONADO") 
    
    # MONTO: Alineado a la DERECHA (width - 2.2cm)
    c.setFillColorRGB(0.89, 0.04, 0.08)
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(width - 2.2*cm, y_total + 0.4*cm, f"$ {row['monto']:,.2f}") 

    # --- 6. PIE DE PÁGINA ---
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica-Oblique", 8)
    hash_seguridad = f"AUTH-{row['idCuota']}Z{row['dni'][-4:]}"
    c.drawCentredString(width/2, 2*cm, f"Código de autenticación: {hash_seguridad}")
    c.drawCentredString(width/2, 1.5*cm, "Gimnasio Abito - Las Breñas, Chaco")

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


