
from pydantic import BaseModel
from datetime import date
from typing import Optional

# Agrega esta clase si no la tienes
class CuotaBase(BaseModel):
    idCuota: int
    pagada: bool
    monto: float
    mes: str
    anio: int
    metodoDePago: Optional[str] = None # <--- Nuevo campo
    idFacturacion: Optional[int] = None # <--- Nuevo campo

class CuotaResponseAlumnoAuth(CuotaBase):
    trabajo: str
    suscripcion: str
    vencimiento: date
    comienzo: date

# Este será el modelo para la respuesta de la API
class CuotaResponsePorDNI(CuotaBase):
    dni: str
    fechaComienzo: date
    vencimiento: date
    trabajo: str
    suscripcion: str



