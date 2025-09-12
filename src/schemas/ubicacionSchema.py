from pydantic import BaseModel, Field, ConfigDict
from typing import List

# =========== PROVINCIA ===========
class ProvinciaBase(BaseModel):
    nomProvincia: str = Field(..., max_length=40,
                            description="Nombre de la Provincia",
                            examples=["Chaco", "Santa Fe", "Buenos Aires"])

class ProvinciaCreate(ProvinciaBase):
    pass

class ProvinciaResponse(ProvinciaBase):
    model_config = ConfigDict(from_attributes=True)

# =========== LOCALIDAD ===========
class LocalidadBase(BaseModel):
    nomLocalidad: str = Field(..., max_length=40,
                            description="Nombre de la localidad", 
                            examples=["Resistencia", "Barranqueras", "Fontana"])
    nomProvincia: str = Field(..., description="Nombre de la Provincia",
                            examples=["Chaco", "Santa Fe"])  # ← Ejemplos reales

class LocalidadCreate(LocalidadBase):
    pass

class LocalidadResponse(LocalidadBase):
    model_config = ConfigDict(from_attributes=True)

# Nuevo schema para respuesta agrupada
class ProvinciaConLocalidades(BaseModel):
    provincia: str = Field(..., description="Nombre de la provincia")
    localidades: List[str] = Field(..., description="Lista de localidades")