
from pydantic import BaseModel, Field
from datetime import date

class CuotaResponse(BaseModel):
    idCuota: int = Field(..., description="ID único de la cuota")
    mes: str
    anio: int # El año se extraerá de la fecha
    trabajo: str
    suscripcion: str
    monto: float # En Python, los tipos NUMERIC de la DB se manejan mejor como float o Decimal
    pagada: bool
    vencimiento: date # Las fechas se devuelven en formato "YYYY-MM-DD"

    class Config:
        from_attributes = True

