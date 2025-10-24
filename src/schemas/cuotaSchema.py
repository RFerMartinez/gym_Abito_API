
from pydantic import BaseModel
from datetime import date

# Agrega esta clase si no la tienes
class CuotaBase(BaseModel):
    pagada: bool
    monto: float
    fechaComienzo: date
    fechaFin: date
    mes: str
    nombreTrabajo: str
    nombreSuscripcion: str

# Este será el modelo para la respuesta de la API
class CuotaResponse(CuotaBase):
    idCuota: int
    dni: str

    class Config:
        from_attributes = True # Permite que Pydantic lea datos desde objetos (ORM mode)