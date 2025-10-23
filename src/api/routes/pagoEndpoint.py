
from fastapi import APIRouter, Depends, Request, status
from asyncpg import Connection

from core.config import settings
from core.session import get_db

from schemas.pagoSchema import (
    PreferenciaCreate,
    PreferenciaResponse
)
from services.pagoServices import (
    crear_preferencia_pago,
    procesar_notificacion_pago
)

# Podrías querer proteger esta ruta para que solo usuarios logueados puedan pagar
from api.dependencies.auth import get_current_user 

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Error interno del servidor"}
    }
)

@router.post(
    "/crear-preferencia",
    response_model=PreferenciaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una preferencia de pago",
    dependencies=[Depends(get_current_user)] # Ruta protegida
)
async def crear_preferencia(
    preferencia_data: PreferenciaCreate
):
    """
    Genera una preferencia de pago en Mercado Pago para una cuota específica.
    Devuelve el ID de la preferencia y la Public Key para el frontend.
    """
    preference_id = await crear_preferencia_pago(preferencia_data)
    return PreferenciaResponse(
        preference_id=preference_id,
        public_key=settings.MP_PUBLIC_KEY # <-- Enviamos la public key
    )


# Endpoint para recibir notificaciones (Webhooks) de Mercado Pago
@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Recibir notificaciones de Mercado Pago",
    include_in_schema=False # Opcional: oculta este endpoint de la doc de Swagger
)
async def recibir_webhook_mercadopago(
    request: Request, 
    db: Connection = Depends(get_db)
):
    """
    Endpoint para recibir notificaciones automáticas de Mercado Pago (Webhooks).
    """
    data = await request.json()
    
    print("🔔 Webhook de Mercado Pago recibido:")
    print(data)
    
    # Llamamos a nuestro servicio para que se encargue de la lógica
    await procesar_notificacion_pago(db, data)
    
    return {"status": "ok"}