import mercadopago
from asyncpg import Connection
from fastapi import HTTPException, status

from core.config import settings
from utils.exceptions import NotFoundException, DatabaseException
from schemas.pagoSchema import PreferenciaPagoResponse

# Inicializamos el SDK de MercadoPago con tu Token
sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN.get_secret_value())

# -------------------------
# Crear preferencia de pago
# -------------------------
async def crear_preferencia_pago(conn: Connection, id_cuota: int) -> PreferenciaPagoResponse:
    """
    Genera una preferencia de pago en MercadoPago para una cuota específica.
    """
    try:
        # 1. Buscar la cuota en la BD para obtener el monto real y verificar que exista
        # (Nunca confíes en el monto que viene del frontend)
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
        # Aquí usamos la URL de Ngrok que generaste (deberías ponerla en tu .env)
        # Por ahora la hardcodeamos o la tomamos de config si la agregas
        # Ejemplo: settings.BACKEND_DOMAIN = "https://tu-url-ngrok.app"
        
        # NOTA: Reemplaza ESTA variable con tu URL de Ngrok actual
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

            # A dónde vuelve el usuario según el resultado
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


        print("--- DEBUG PREFERENCIA ---")
        print(preference_data)  # <--- Agrega esto para ver qué se envía
        print("-------------------------")


        # 3. Crear la preferencia en la API de MercadoPago
        preference_response = sdk.preference().create(preference_data)
        
        if preference_response["status"] != 201:
            raise Exception(f"Error al crear preferencia en MP: {preference_response}")

        response_data = preference_response["response"]

        return PreferenciaPagoResponse(
            init_point=response_data["init_point"], # URL para producción
            sandbox_init_point=response_data["sandbox_init_point"] # URL para pruebas
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
            query = 'UPDATE "Cuota" SET pagada = TRUE WHERE "idCuota" = $1'
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

