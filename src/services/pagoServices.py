
import mercadopago
from asyncpg import Connection # <-- Importante para la base de datos

from core.config import settings
from schemas.pagoSchema import PreferenciaCreate
from utils.exceptions import AppException, DatabaseException

# Inicializamos el SDK de Mercado Pago una sola vez
sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN.get_secret_value())

async def crear_preferencia_pago(preferencia_data: PreferenciaCreate) -> str:
    """
    Crea una preferencia de pago en Mercado Pago y devuelve su ID.
    """
    try:
        # Convertimos el ítem de Pydantic a un diccionario
        items_dict = [item.model_dump() for item in preferencia_data.items]

        # Datos de la preferencia que enviaremos a Mercado Pago
        datos_preferencia = {
            "items": items_dict,
            # ¡ESTA ES LA PARTE CLAVE!
            # Guardamos el id de nuestra cuota para identificarla en el webhook
            "external_reference": str(preferencia_data.id_cuota),
            "back_urls": {
                "success": f"{settings.FRONTEND_URL}/pago-exitoso",
                "failure": f"{settings.FRONTEND_URL}/pago-fallido",
            },
            "notification_url": f"{settings.BACKEND_URL}/pagos/webhook"
        }

        # Creamos la preferencia usando el SDK
        respuesta_preferencia = sdk.preference().create(datos_preferencia)

        if respuesta_preferencia["status"] == 201:
            # Extraemos el ID de la preferencia
            preference_id = respuesta_preferencia["response"]["id"]
            return preference_id
        else:
            # Si Mercado Pago devuelve un error, lo lanzamos
            raise AppException(
                detail=f"Error al crear preferencia en Mercado Pago: {respuesta_preferencia['response']}",
                status_code=respuesta_preferencia["status"]
            )
            
    except Exception as e:
        # Capturamos cualquier otro error inesperado
        raise DatabaseException("crear preferencia de pago", str(e))

async def procesar_notificacion_pago(db: Connection, data: dict):
    """
    Procesa la notificación de Mercado Pago, verifica el pago y actualiza la BD.
    """
    if data.get("type") == "payment":
        payment_id = data.get("data", {}).get("id")
        if not payment_id:
            return

        try:
            # 1. Obtener los detalles completos del pago desde Mercado Pago
            payment_info_response = sdk.payment().get(payment_id)
            payment_info = payment_info_response.get("response", {})
            
            # 2. Verificar que el pago esté aprobado
            if payment_info.get("status") == "approved":
                # 3. Recuperar el ID de nuestra cuota desde external_reference
                id_cuota_str = payment_info.get("external_reference")
                if not id_cuota_str:
                    print(f"⚠️  Webhook para pago {payment_id} recibido sin external_reference.")
                    return
                
                id_cuota = int(id_cuota_str)
                
                # 4. Actualizar la base de datos
                # Buscamos la cuota por su ID y DNI (por seguridad)
                # La tabla Cuota tiene una clave primaria compuesta (dni, idCuota)
                result = await db.execute(
                    'UPDATE "Cuota" SET pagada = TRUE WHERE "idCuota" = $1 AND pagada = FALSE',
                    id_cuota
                )

                if result == "UPDATE 1":
                    print(f"✅ Cuota {id_cuota} marcada como pagada.")
                else:
                    # Esto puede pasar si el webhook llega dos veces o la cuota no existe
                    print(f"ℹ️  No se actualizó la cuota {id_cuota}. Pudo haber sido pagada previamente.")

        except Exception as e:
            # Es importante capturar errores para que MP no siga reintentando indefinidamente
            print(f"❌ Error procesando webhook para pago {payment_id}: {e}")
            raise DatabaseException("procesar webhook", str(e))