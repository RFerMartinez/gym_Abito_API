from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import List, Optional

# Esquema para los horarios que se asignarán al empleado
class HorarioEmpleadoCreate(BaseModel):
    dia: str = Field(..., description="Día de la semana")
    nroGrupo: str = Field(..., description="Número de grupo")

# Esquema principal para crear un empleado
class EmpleadoCreate(BaseModel):
    # Datos Personales
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]+$", description="DNI")
    nombre: str = Field(..., max_length=40)
    apellido: str = Field(..., max_length=40)
    sexo: str = Field(..., max_length=1, description="'M' o 'F'")
    email: EmailStr = Field(...)
    telefono: str = Field(..., max_length=15)
    
    # Datos de Dirección
    nomProvincia: str = Field(..., max_length=40)
    nomLocalidad: str = Field(..., max_length=40)
    calle: str = Field(..., max_length=60)
    numero: str = Field(default="S/N", max_length=5)
    
    # Datos del Empleado
    rol: str = Field(..., description="Rol del empleado (ej: Profesor, Limpieza, Recepción)")
    
    # Lista de horarios a asignar (puede estar vacía)
    horarios: List[HorarioEmpleadoCreate] = Field(default=[], description="Lista de grupos asignados")

    @field_validator('sexo')
    @classmethod
    def validar_sexo(cls, v: str) -> str:
        if v.upper() not in ['M', 'F']:
            raise ValueError("Sexo debe ser 'M' o 'F'")
        return v.upper()

class EmpleadoResponse(BaseModel):
    dni: str
    nombre: str
    apellido: str
    email: str
    rol: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class EmpleadoListado(BaseModel):
    dni: str
    nombre: str
    apellido: str
    rol: str

    model_config = ConfigDict(from_attributes=True)
class HorarioEmpleadoResponse(BaseModel):
    dia: str
    nroGrupo: str

    model_config = ConfigDict(from_attributes=True)

# Schema para el detalle completo del empleado
class EmpleadoDetalle(BaseModel):
    dni: str
    nombre: str
    apellido: str
    sexo: str
    email: str
    telefono: str
    
    # Datos de Dirección
    provincia: Optional[str] = None # Mapeado desde 'nomProvincia'
    localidad: Optional[str] = None # Mapeado desde 'nomLocalidad'
    calle: Optional[str] = None
    nro: Optional[str] = None
    
    # Datos de Rol
    rol: str
    
    # Lista de horarios
    horarios: List[HorarioEmpleadoResponse] = []

    model_config = ConfigDict(from_attributes=True)

class EmpleadoHorariosUpdate(BaseModel):
    horarios: List[HorarioEmpleadoCreate]

