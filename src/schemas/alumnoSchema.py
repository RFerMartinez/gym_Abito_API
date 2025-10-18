
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# Esquema para la asignación de horario
class HorarioAsignado(BaseModel):
    nroGrupo: str = Field(..., description="Número de grupo al que asiste")
    dia: str = Field(..., description="Día de la semana de asistencia")

# Esquema para la activación de un alumno
class AlumnoActivate(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]+$",
                    description="DNI de la persona a activar como alumno")
    sexo: str = Field(..., max_length=1, description="Sexo del alumno (ej: 'M', 'F')")
    nombreTrabajo: str = Field(..., description="Nombre del trabajo asignado")
    nombreSuscripcion: str = Field(..., description="Nombre de la suscripción")
    nivel: Optional[str] = Field(None, max_length=3, description="Nivel del alumno (ej: 'A1')")
    deporte: Optional[str] = Field(None, max_length=20, description="Deporte que practica (si aplica)")
    horarios: List[HorarioAsignado] = Field(..., description="Lista de horarios asignados al alumno")

    @field_validator('sexo')
    @classmethod
    def validar_sexo(cls, v: str) -> str:
        sexo_upper = v.upper()
        if sexo_upper not in ['M', 'F']:
            raise ValueError("El sexo debe ser 'M' o 'F'")
        return sexo_upper

# Esquema para la respuesta tras la activación
class AlumnoActivateResponse(BaseModel):
    dni: str
    nombre: str
    apellido: str
    email: str
    message: str