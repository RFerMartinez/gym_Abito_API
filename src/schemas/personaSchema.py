# src/schemas/personaSchema.py
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional

# Schema para Req 1: Listar todas las personas
class PersonaListado(BaseModel):
    """Esquema simple para listar personas."""
    dni: str = Field(..., description="DNI de la persona")
    nombre: str = Field(..., description="Nombre de la persona")
    apellido: str = Field(..., description="Apellido de la persona")

    model_config = ConfigDict(from_attributes=True)

# Schema para Req 2: Obtener detalles de una persona
class PersonaDetalle(BaseModel):
    """Esquema detallado para una persona específica."""
    dni: str
    nombre: str
    apellido: str
    telefono: str
    email: EmailStr
    usuario: str
    requiereCambioClave: bool
    sexo: Optional[str] = None
    
    # Información de la tabla Direccion
    provincia: Optional[str] = None
    localidad: Optional[str] = None
    calle: Optional[str] = None
    nro: Optional[str] = None

    # Información de roles
    esAdmin: bool
    es_alumno: bool = Field(False, description="Indica si la persona es un alumno")
    es_empleado: bool = Field(False, description="Indica si la persona es un empleado")

    model_config = ConfigDict(from_attributes=True)

