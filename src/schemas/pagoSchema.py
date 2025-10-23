
from pydantic import BaseModel, Field
from typing import List, Optional

# Esquema para el ítem que se va a pagar (ej. una cuota)
class PagoItem(BaseModel):
    id: Optional[str] = Field(None, description="ID del ítem en tu sistema (ej. idCuota)")
    title: str = Field(..., description="Descripción del ítem")
    quantity: int = Field(1, description="Cantidad (siempre será 1 para una cuota)")
    unit_price: float = Field(..., gt=0, description="Precio unitario")
    currency_id: str = Field("ARS", description="Moneda")

# Esquema para la solicitud de creación de preferencia
class PreferenciaCreate(BaseModel):
    items: List[PagoItem]
    id_cuota: int = Field(..., description="ID de la cuota que se está pagando")

# Esquema para la respuesta que enviamos al frontend
class PreferenciaResponse(BaseModel):
    preference_id: str = Field(..., description="ID de la preferencia de pago")
    public_key: str = Field(..., description="Public Key de Mercado Pago para el frontend")

