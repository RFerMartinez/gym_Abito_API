
from pydantic import BaseModel, EmailStr, Field, field_validator
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

class HorariosUpdate(BaseModel):
    horarios: List[HorarioAlumno] = Field(..., description="La lista completa y nueva de horarios para el alumno.")

class AlumnoPerfilUpdate(BaseModel):
    nombre: str = Field(..., max_length=40, description="Nombre de la persona")
    apellido: str = Field(..., max_length=40, description="Apellido de la persona")
    sexo: str = Field(..., max_length=1, description="Sexo ('M' o 'F')")
    email: EmailStr = Field(..., description="Email de la persona")
    telefono: str = Field(..., max_length=15, description="Teléfono de la persona")
    nomProvincia: str = Field(..., max_length=40, description="Nombre de la provincia")
    nomLocalidad: str = Field(..., max_length=40, description="Nombre de la localidad")
    calle: str = Field(..., max_length=60, description="Calle")
    numero: str = Field(default="S/N", max_length=5, description="Número de calle")

    @field_validator('sexo')
    @classmethod
    def validar_sexo(cls, v: str) -> str:
        sexo_upper = v.upper()
        if sexo_upper not in ['M', 'F']:
            raise ValueError("El sexo debe ser 'M' o 'F'")
        return sexo_upper

    @field_validator('numero')
    @classmethod
    def validar_numero(cls, v: str) -> str:
        # Re-utilizamos la validación de tu schema de Direccion
        if v != "S/N" and not v.isdigit():
            raise ValueError("El número debe ser 'S/N' o un valor numérico")
        return v
