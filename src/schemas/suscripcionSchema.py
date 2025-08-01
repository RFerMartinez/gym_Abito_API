from pydantic import BaseModel, Field
from typing import Optional

class SuscripcionBase(BaseModel):
    nombreSuscripcion: str = Field(..., max_length=40)
    precio: float

class SuscripcionCreate(SuscripcionBase):
    pass

class SuscripcionUpdatePrice(SuscripcionBase):
    precio: Optional[float] = None

class SuscripcionCreateResponse(BaseModel):
    pass


