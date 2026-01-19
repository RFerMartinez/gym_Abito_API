from pydantic import BaseModel
from datetime import date, datetime
from typing import List

class FacturacionResponse(BaseModel):
    idFacturacion: int
    fechaInicio: date
    fechaFin: date
    fechaGeneracion: datetime
    montoTotal: float
    cantidadCuotas: int

class ReporteDetalleCuota(BaseModel):
    alumno: str
    dni: str
    monto: float
    fechaPago: date
    metodoDePago: str