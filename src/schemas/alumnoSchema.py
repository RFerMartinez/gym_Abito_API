
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
    nombreTrabajo: str = Field(..., description="Nombre del trabajo asignado")
    nombreSuscripcion: str = Field(..., description="Nombre de la suscripción")
    nivel: Optional[str] = Field(None, max_length=3, description="Nivel del alumno (ej: 'A1')")
    deporte: Optional[str] = Field(None, max_length=20, description="Deporte que practica (si aplica)")
    horarios: List[HorarioAsignado] = Field(..., description="Lista de horarios asignados al alumno")

# Esquema para la respuesta tras la activación
class AlumnoActivateResponse(BaseModel):
    dni: str
    nombre: str
    apellido: str
    email: str
    message: str

# === ESQUEMA NUEVO PARA EL LISTADO DE ALUMNOS ===
class AlumnoListado(BaseModel):
    dni: str = Field(..., description="DNI del alumno")
    nombre: str = Field(..., description="Nombre del alumno")
    apellido: str = Field(..., description="Apellido del alumno")
    activo: bool = Field(..., description="Indica si el alumno está activo")
    cuotasPendientes: int = Field(..., description="Cantidad de cuotas impagas")
    turno: str = Field(..., description="Turno asignado (Mañana, Tarde, No asignado)")

    class Config:
        from_attributes = True

# === ESQUEMA NUEVO PARA EL DETALLE DE UN ALUMNO ===
class AlumnoDetalle(BaseModel):
    dni: str
    nombre: str
    apellido: str
    sexo: str
    email: str
    telefono: str
    activo: bool
    cuotasPendientes: int
    turno: str
    suscripcion: str
    trabajoactual: str
    nivel: str
    provincia: Optional[str] = None
    localidad: Optional[str] = None
    calle: Optional[str] = None
    nro: Optional[str] = None

    class Config:
        from_attributes = True

# === ESQUEMA MODIFICADO PARA EL HORARIO DEL ALUMNO ===
class HorarioAlumno(BaseModel):
    dia: str
    nroGrupo: str # <--- Volvemos a nroGrupo

    class Config:
        from_attributes = True

# === NUEVO ESQUEMA CONTENEDOR PARA LA RESPUESTA COMPLETA ===
class HorariosAlumnoResponse(BaseModel):
    horarios: List[HorarioAlumno]

