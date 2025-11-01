from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo
from typing import List, Optional
from datetime import time
import re

# ====-- DIAS --====
class DiaBase(BaseModel):
    dia: str = Field(..., min_length=4, max_length=10,  # CORREGIDO: max_length en lugar de max_digits
                    description="Nombre del día de la semana",
                    examples=["Lunes", "Martes", "Miércoles"])
    
    @field_validator('dia')
    @classmethod
    def validar_dia(cls, value: str) -> str:
        dias_validos = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        if value.capitalize() not in dias_validos:
            raise ValueError(f"Día no válido. Debe ser uno de: {', '.join(dias_validos)}")
        return value.capitalize()

class DiaCreate(DiaBase):
    pass

class DiaResponse(DiaBase):
    model_config = ConfigDict(from_attributes=True)

# ====-- HORARIOS --====
class HorarioBase(BaseModel):
    nroGrupo: str = Field(..., min_length=1, max_length=2, 
                        description="Número identificador del grupo",
                        examples=["1", "2", "A", "B"])
    horaInicio: time = Field(..., description="Hora de inicio del horario",
                            examples=["07:00:00"])
    horaFin: time = Field(..., description="Hora de fin del horario",
                        examples=["09:00:00"])

    @field_validator('horaFin')
    @classmethod
    def validar_horario(cls, v: time, values: ValidationInfo) -> time:  # Usa ValidationInfo
        # Accede a los datos validados a través de values.data
        if values.data is not None and 'horaInicio' in values.data:
            hora_inicio = values.data['horaInicio']
            if v <= hora_inicio:
                raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return v
    
    @field_validator('nroGrupo')
    @classmethod
    def validar_nro_grupo(cls, value: str) -> str:
        # Eliminar espacios en blanco al inicio y final
        value_clean = value.strip().upper()
        
        if not re.match(r'^[A-Z0-9]{1,2}$', value_clean):
            raise ValueError("El número de grupo debe contener solo letras o números (1-2 caracteres)")
        
        return value_clean

class HorarioCreate(HorarioBase):
    pass

class HorarioResponse(HorarioBase):
    model_config = ConfigDict(from_attributes=True)

# ====-- PERTENECE --====
# Schema para la relación muchos-a-muchos
class PerteneceBase(BaseModel):
    nroGrupo: str = Field(..., description="Número del grupo (FK a Horario)", examples=["1"])
    dia: str = Field(..., description="Día de la semana (FK a Dia)", examples=["Lunes"])
    capacidadMax: int = Field(..., ge=1, le=50, 
                            description="Capacidad máxima de alumnos para este grupo-día",
                            examples=[20])
    dniEmpleado: Optional[str] = Field(
        None, min_length=8, max_length=8, pattern="^[0-9]+$",
        description="DNI del empleado asignado (opcional, FK a Empleado)",
        examples=["12345678"]
    )

    @field_validator('dia')
    @classmethod
    def validar_dia_existente(cls, value: str) -> str:
        # Esta validación debería verificar contra la base de datos
        # Por ahora solo validamos formato
        dias_validos = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        if value.capitalize() not in dias_validos:
            raise ValueError(f"Día no válido. Debe ser uno de: {', '.join(dias_validos)}")
        return value.capitalize()

    @field_validator('nroGrupo')
    @classmethod
    def validar_nro_grupo(cls, value: str) -> str:
        # Eliminar espacios en blanco al inicio y final
        value_clean = value.strip().upper()
        
        if not re.match(r'^[A-Z0-9]{1,2}$', value_clean):
            raise ValueError("El número de grupo debe contener solo letras o números (1-2 caracteres)")
        
        return value_clean

    @field_validator('dniEmpleado')
    @classmethod
    def validar_dni_empleado(cls, value: Optional[str]) -> Optional[str]:
        if value and not value.isdigit():
            raise ValueError("El DNI debe contener solo números")
        return value

    @field_validator('capacidadMax')
    @classmethod
    def validar_capacidad(cls, value: int) -> int:
        if value < 1:
            raise ValueError("La capacidad máxima debe ser al menos 1")
        if value > 100:
            raise ValueError("La capacidad máxima no puede exceder 100")
        return value

class PerteneceCreate(PerteneceBase):
    pass

class PerteneceResponse(PerteneceBase):
    model_config = ConfigDict(from_attributes=True)

# ====-- SCHEMAS PARA RESPUESTAS COMBINADAS --====
class DiaConCapacidad(BaseModel):
    dia: str = Field(..., description="Día de la semana")
    capacidadMax: int = Field(..., description="Capacidad máxima para este día")
    empleado: Optional[str] = Field(None, description="Empleado asignado para este día")
    alumnos_inscritos: Optional[int] = Field(0, description="Cantidad de alumnos inscritos")

class HorarioCompletoResponse(HorarioResponse):
    dias_asignados: List[DiaConCapacidad] = Field(..., description="Días asignados con su capacidad")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nroGrupo": "1",
                "horaInicio": "07:00:00",
                "horaFin": "09:00:00",
                "dias_asignados": [
                    {"dia": "Lunes", "capacidadMax": 20, "empleado": "12345678", "alumnos_inscritos": 15},
                    {"dia": "Miércoles", "capacidadMax": 15, "empleado": None, "alumnos_inscritos": 10}
                ]
            }
        }
    )

class GrupoConDetalles(BaseModel):
    nroGrupo: str = Field(..., description="Número del grupo")
    horario: HorarioResponse = Field(..., description="Información del horario")
    dias: List[DiaConCapacidad] = Field(..., description="Días con capacidad y empleado")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nroGrupo": "1",
                "horario": {
                    "nroGrupo": "1",
                    "horaInicio": "07:00:00",
                    "horaFin": "09:00:00"
                },
                "dias": [
                    {"dia": "Lunes", "capacidadMax": 20, "empleado": "12345678", "alumnos_inscritos": 15},
                    {"dia": "Miércoles", "capacidadMax": 15, "empleado": None, "alumnos_inscritos": 10}
                ]
            }
        }
    )

# ====-- SCHEMAS PARA ACTUALIZACIÓN --====
class UpdateCapacidadGrupo(BaseModel):
    capacidadMax: int = Field(..., ge=1, le=50, 
                            description="Nueva capacidad máxima",
                            examples=[25])

class UpdateEmpleadoGrupo(BaseModel):
    dniEmpleado: Optional[str] = Field(
        None, min_length=8, max_length=8, pattern="^[0-9]+$",
        description="Nuevo DNI del empleado asignado",
        examples=["87654321"]
    )

# ====-- SCHEMA PARA ESTADÍSTICAS --====
class GrupoEstadisticasResponse(BaseModel):
    nroGrupo: str
    dia: str
    capacidadMax: int
    alumnos_inscritos: int = Field(..., ge=0, description="Número de alumnos inscritos")
    disponibilidad: int = Field(..., description="Espacios disponibles")
    porcentaje_ocupacion: float = Field(..., ge=0, le=100, 
                                    description="Porcentaje de ocupación")

    model_config = ConfigDict(from_attributes=True)

# schema para creacion de un uevo grupo desde FrontEnd
class DiaAsignadoCreate(BaseModel):
    """
    Schema interno para definir un día asignado durante la creación
    del grupo completo.
    """
    dia: str = Field(..., description="Nombre del día de la semana (Lunes, Martes, etc.)")
    capacidadMax: int = Field(..., ge=1, le=50, description="Capacidad máxima")
    dniEmpleado: Optional[str] = Field(None, min_length=8, max_length=8, pattern="^[0-9]+$", description="DNI del empleado (opcional)")

    @field_validator('dia')
    @classmethod
    def validar_dia_existente(cls, value: str) -> str:
        # Validamos el formato del día
        dias_validos = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        if value.capitalize() not in dias_validos:
            raise ValueError(f"Día no válido. Debe ser uno de: {', '.join(dias_validos)}")
        return value.capitalize()

class HorarioCompletoCreate(HorarioBase):
    """
    Schema principal para el payload de creación de un grupo
    con sus días ya asignados.
    """
    dias_asignados: List[DiaAsignadoCreate] = Field(..., description="Lista de días a asignar al grupo")