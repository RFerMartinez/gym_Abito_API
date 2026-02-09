from pydantic import BaseModel
from datetime import date, datetime, time
from typing import List, Optional

# Modelo base para la Factura
class FacturacionBase(BaseModel):
    fechaInicio: date
    fechaFin: date
    fechaGeneracion: datetime
    montoTotal: float
    cantidadCuotas: int
    titular: str

# Modelo completo con ID (Salida)
class FacturacionResponse(FacturacionBase):
    idFacturacion: int

    class Config:
        from_attributes = True

# --- Modelos para el Reporte Detallado ---

class DetalleCuotaFactura(BaseModel):
    idCuota: int
    dni: str
    alumno: str
    monto: float
    fechaPago: Optional[date]
    horaDePago: Optional[time] = None
    metodoDePago: Optional[str]
    concepto: str 

class ReporteFacturacion(FacturacionResponse):
    detalles: List[DetalleCuotaFactura]

