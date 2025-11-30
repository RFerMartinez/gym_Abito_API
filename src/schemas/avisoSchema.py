from pydantic import BaseModel, Field, ConfigDict
from datetime import date, time
from typing import Optional

# Base común
class AvisoBase(BaseModel):
    descripcion: str = Field(..., min_length=5, description="Contenido del aviso")

# Para CREAR: Solo necesitamos el texto
class AvisoCreate(AvisoBase):
    pass

# Para ACTUALIZAR: Solo permitimos editar el texto (la fecha original se mantiene)
class AvisoUpdate(BaseModel):
    descripcion: str = Field(..., min_length=5, description="Nuevo contenido del aviso")

# Para RESPUESTA: Aquí sí incluimos todo (ID, fechas, autor)
class AvisoResponse(AvisoBase):
    idAviso: int
    fecha: date
    hora: time
    dni: str # DNI del autor del aviso
    
    # Opcional: Podrías querer devolver el nombre del autor también si haces un JOIN
    # nombre_autor: Optional[str] = None 

    model_config = ConfigDict(from_attributes=True)

