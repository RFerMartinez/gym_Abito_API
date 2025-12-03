from pydantic import BaseModel

class PreferenciaPagoResponse(BaseModel):
    """
    Respuesta que enviaremos al Frontend con la URL 
    para redirigir al usuario a Mercado Pago.
    """
    init_point: str  # URL para abrir el modal/checkout
    sandbox_init_point: str # URL para pruebas (Sandbox)

class WebhookNotification(BaseModel):
    """
    Estructura básica de la notificación que envía MercadoPago.
    """
    id: str
    live_mode: bool
    type: str
    date_created: str
    user_id: str
    api_version: str
    action: str
    data: dict

