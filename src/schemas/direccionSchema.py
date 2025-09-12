from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional

class DireccionBase(BaseModel):
    nomLocalidad: str = Field(..., max_length=40, description="Nombre de la localidad")
    nomProvincia: str = Field(..., max_length=40, description="Nombre de la provincia")
    numero: str = Field(default="S/N", max_length=5, description="Número de calle")
    calle: str = Field(..., max_length=60, description="Nombre de la calle")
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]+$",
                    description="DNI de la persona asociada")

    @field_validator('numero')
    @classmethod
    def validar_numero(cls, v: str) -> str:
        if v != "S/N" and not v.isdigit():
            raise ValueError("El número debe ser 'S/N' o un valor numérico")
        return v

    @field_validator('calle')
    @classmethod
    def validar_calle(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La calle no puede estar vacía")
        if len(v.strip()) < 3:
            raise ValueError("La calle debe tener al menos 3 caracteres")
        return v.strip()

class DireccionCreate(DireccionBase):
    pass

class DireccionResponse(DireccionBase):
    idDireccion: int = Field(..., description="ID único de la dirección")
    model_config = ConfigDict(from_attributes=True)

# Schema corregido sin objetos anidados
class DireccionCompletaResponse(BaseModel):
    idDireccion: int
    nomLocalidad: str
    nomProvincia: str
    numero: str
    calle: str
    dni: str
    nombre_localidad: str = Field(..., description="Nombre completo de la localidad")
    nombre_provincia: str = Field(..., description="Nombre completo de la provincia")
    
    model_config = ConfigDict(from_attributes=True)