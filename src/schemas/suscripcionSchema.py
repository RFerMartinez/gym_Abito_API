from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# --- Esquema Base ---
# Define los campos fundamentales y sus validaciones.
# Se usará como base para la creación y la respuesta.
class SuscripcionBase(BaseModel):
    nombreSuscripcion: str = Field(
        ..., 
        max_length=40, 
        description="Nombre único de la suscripción",
        examples=["5 días a la semana", "3 días a la semana"]
    )
    precio: float = Field(
        ..., 
        gt=0, 
        description="Precio de la suscripción. Debe ser mayor a 0."
    )

# --- Esquema de Creación ---
# Se utiliza para validar el body de un POST.
class SuscripcionCreate(SuscripcionBase):
    pass

# --- Esquema de Actualización ---
# Se utiliza para validar el body de un PATCH.
# Solo incluye los campos que se pueden modificar.
class SuscripcionUpdate(BaseModel):
    precio: float = Field(
        ..., 
        gt=0, 
        description="El nuevo precio de la suscripción."
    )

# --- Esquema de Respuesta ---
# Se utiliza como response_model para GET, POST, PATCH y PUT.
# Hereda de SuscripcionBase y añade la configuración para
# mapear desde el objeto de la base de datos (from_attributes=True).
class SuscripcionResponse(SuscripcionBase):
    """Esquema de respuesta para una suscripción."""
    
    # ConfigDict es la forma moderna (Pydantic v2) de 'class Config'.
    model_config = ConfigDict(
        from_attributes=True  # Permite crear el modelo desde objetos de la BD
    )