
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time

class ReclamoBase(BaseModel):
    comentario: str = Field(..., min_length=10, description="Descripción detallada del reclamo.")

class ReclamoCreate(ReclamoBase):
    pass

class ReclamoUpdate(BaseModel):
    comentario: str = Field(..., min_length=10, description="Nuevo texto del comentario para el reclamo.")

class ReclamoResponse(ReclamoBase):
    idReclamo: int
    fecha: date
    hora: time
    dni: str

    class Config:
        from_attributes = True

