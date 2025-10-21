from pydantic import BaseModel, Field
from typing import Optional

class SuscripcionBase(BaseModel):
    nombreSuscripcion: str = Field(..., max_length=40)
    precio: float

class SuscripcionCreate(SuscripcionBase):
    pass


# Solo contiene los campos que se pueden modificar.
class SuscripcionUpdate(BaseModel):
    precio: float = Field(..., gt=0, description="El nuevo precio de la suscripción.")

# El esquema 'SuscripcionUpdatePrice' ya no es necesario para este flujo.
class SuscripcionUpdatePrice(SuscripcionBase):
    precio: Optional[float] = None

class SuscripcionCreateResponse(BaseModel):
    # Este esquema parece estar vacío, lo cual es válido si no se necesita
    # devolver un cuerpo en la respuesta de creación.
    pass


