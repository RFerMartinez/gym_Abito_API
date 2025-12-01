
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time

class ReclamoBase(BaseModel):
    comentario: str = Field(..., description="Descripción detallada del reclamo.")

class ReclamoCreate(ReclamoBase):
    pass

class ReclamoUpdate(BaseModel):
    comentario: str = Field(..., description="Nuevo texto del comentario para el reclamo.")

class ReclamoResponse(ReclamoBase):
    idReclamo: int
    fecha: date
    hora: time
    dni: str

    class Config:
        from_attributes = True

class ReclamoListadoAdmin(ReclamoResponse):
    nombre: str = Field(..., description="Nombre del alumno")
    apellido: str = Field(..., description="Apellido del alumno")
    

