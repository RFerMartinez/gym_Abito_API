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
