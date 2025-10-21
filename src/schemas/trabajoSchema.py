from pydantic import BaseModel, Field, field_validator
from typing import Optional

# SCHEMA para crear un trabajo nevo
class TrabajoBase(BaseModel):
    # Esquema base para trabajo con validaciones básicas
    nombreTrabajo: str = Field(..., max_length=20, description="Nombre único del trabajo", examples=["Preparación Física"])
    descripcion: str = Field(..., description="Descripción detallada del trabajo", examples=["Preparación para Tenis"])

    # @field_validator('nombreTrabajo')
    # def validar_nombre_trabajo(cls, value):
    #     # Validar que no contenga caracteres especiales
    #     if not value.replace(" ", "").isalnum():
    #         raise ValueError("El nombre solo puede contener letras, números y esoacios")
    #     return value.strip()

class TrabajoCreate(TrabajoBase):
    # Esquema para la creación de trabajos
    pass

class UpdateTrabajoDescr(TrabajoBase):
    descripcion: Optional[str] = Field(None, description="Nueva descripción del trabajo")

# Usaremos este esquema para el cuerpo (body) de la petición PUT.
class TrabajoUpdate(BaseModel):
    descripcion: str = Field(..., description="La nueva descripción para el trabajo.")

class TrabajoInDB(TrabajoBase):
    # Esquema para representar un trabajo en la Base de Datos
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "nombreTrabajo": "Preparación Física",
                "descripcion": "Preparación para Tenis"
            }
        }

# === ESQUEMA MODIFICADO PARA ACTUALIZAR UN TRABAJO ===
# Hereda de TrabajoBase para incluir ambos campos.
class TrabajoUpdateCompleto(TrabajoBase):
    pass