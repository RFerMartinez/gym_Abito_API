# src/schemas/estadisticasSchema.py

from pydantic import BaseModel, Field
from typing import List

class EstadisticaTrabajoData(BaseModel):
    """Define la estructura interna de los datos de estadística por trabajo."""
    nombre: str = Field(..., description="Nombre del trabajo")
    cantidad: int = Field(..., description="Cantidad de alumnos inscritos en este trabajo")

class EstadisticaTrabajoItem(BaseModel):
    """Define la estructura de cada item en la lista de respuesta."""
    id: int = Field(..., description="Identificador secuencial para el frontend")
    data: List[EstadisticaTrabajoData] = Field(..., description="Lista que contiene los datos del trabajo")

    class Config:
        from_attributes = True # Permite crear el modelo desde objetos de base de datos

class DashboardKPIs(BaseModel):
    alumnos_activos: int
    cuotas_vencidas: int
    monto_cuotas_vencidas: float
    ingreso_mensual: float
    cantidad_cobrado: float
    porcentaje_cobro: float

class DatasetTurno(BaseModel):
    label: str          # "Mañana" o "Tarde"
    data: List[int]     # Array de 7 enteros [10, 20, 5, ...]
    backgroundColor: str
    borderColor: str
    borderWidth: int = 1

class GraficoTurnosResponse(BaseModel):
    labels: List[str]   # ["Ene", "Feb", ...]
    datasets: List[DatasetTurno]

class EntrenadorStats(BaseModel):
    nombre: str
    apellido: str
    dni: str
    rol: str
    alumnos_a_cargo: int
    monto_recaudado_mes: float
    cuotas_pendientes: int

