from fastapi import APIRouter, Depends, status, HTTPException
from asyncpg import Connection
from typing import List, Optional

# SESSION
from core.session import get_db

# SERVICES
from services.horarioServices import (
    crear_horario,
    crear_relacion_grupo_dia,
    obtener_horarios_completos,
    obtener_horarios_por_dia_service,
    actualizar_capacidad_grupo,
    eliminar_relacion_grupo_dia
)

# SCHEMAS
from schemas.horarioSchema import (
    HorarioCreate,
    HorarioResponse,
    PerteneceCreate,
    PerteneceResponse,
    HorarioCompletoResponse,
    GrupoConDetalles,
    UpdateCapacidadGrupo,
    UpdateEmpleadoGrupo
)

# Dependencias
from api.dependencies.security import staff_required, admin_required

# BLUEPRINT de /horarios
router = APIRouter(
    prefix="/horarios",
    tags=["horarios"],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Recurso no encontrado"
        },
        status.HTTP_409_CONFLICT: {
            "description": "Conflicto - El recurso ya existe"
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Error en la solicitud"
        }
    }
)

# ===============================================================

# CREAR horario/grupo
@router.post(
    "/",
    response_model=HorarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo horario/grupo (Admin)",
    response_description="Horario creado exitosamente",
    dependencies=[Depends(admin_required)]
)
async def crear_nuevo_horario(
    horario_data: HorarioCreate,
    db: Connection = Depends(get_db)
):
    """
    Crea un nuevo horario/grupo en el sistema.
    
    - **nroGrupo**: Identificador único del grupo (ej: "1", "A", "B1")
    - **horaInicio**: Hora de inicio (formato HH:MM:SS)
    - **horaFin**: Hora de fin (debe ser posterior a horaInicio)
    """
    return await crear_horario(conn=db, horario=horario_data)

# ASIGNAR día a grupo
@router.post(
    "/asignar-dia",
    response_model=PerteneceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar un día a un grupo (admin)",
    response_description="Día asignado al grupo exitosamente",
    dependencies=[Depends(admin_required)]
)
async def asignar_dia_a_grupo(
    pertenece_data: PerteneceCreate,
    db: Connection = Depends(get_db)
):
    """
    Asigna un día específico a un grupo con capacidad y empleado opcional.
    
    - **nroGrupo**: Grupo existente
    - **dia**: Día de la semana (Lunes, Martes, etc.)
    - **capacidadMax**: Capacidad máxima de alumnos
    - **dniEmpleado**: DNI del empleado asignado (opcional)
    """
    return await crear_relacion_grupo_dia(conn=db, pertenece=pertenece_data)

# LISTAR todos los horarios completos
@router.get(
    "/",
    response_model=List[HorarioCompletoResponse],
    summary="Obtener todos los horarios con detalles (Staff)",
    response_description="Lista de horarios con días asignados",
    dependencies=[Depends(staff_required)]
)
async def listar_horarios_completos(
    db: Connection = Depends(get_db)
):
    """
    Obtiene todos los horarios/grupos con sus días asignados,
    capacidad y empleados correspondientes.
    """
    return await obtener_horarios_completos(conn=db)

# OBTENER horarios por día específico
@router.get(
    "/dia/{dia}",
    response_model=List[GrupoConDetalles],
    summary="Obtener horarios por día",
    response_description="Horarios disponibles para el día especificado"
)
async def obtener_horarios_por_dia(
    dia: str,
    db: Connection = Depends(get_db)
):
    """
    Obtiene todos los grupos/horarios disponibles para un día específico.
    
    - **dia**: Día de la semana (Lunes, Martes, Miércoles, etc.)
    """
    return await obtener_horarios_por_dia_service(conn=db, dia=dia)

# ACTUALIZAR capacidad de un grupo-día
@router.patch(
    "/{nroGrupo}/dia/{dia}/capacidad",
    response_model=PerteneceResponse,
    summary="Actualizar capacidad de un grupo en un día",
    response_description="Capacidad actualizada exitosamente"
)
async def actualizar_capacidad(
    nroGrupo: str,
    dia: str,
    capacidad_data: UpdateCapacidadGrupo,
    db: Connection = Depends(get_db)
):
    """
    Actualiza la capacidad máxima para un grupo en un día específico.
    
    - **nroGrupo**: Identificador del grupo
    - **dia**: Día de la semana
    - **capacidadMax**: Nueva capacidad máxima
    """
    result = await actualizar_capacidad_grupo(
        conn=db, 
        nroGrupo=nroGrupo, 
        dia=dia, 
        capacidad=capacidad_data.capacidadMax
    )
    return result

# ACTUALIZAR empleado de un grupo-día
@router.patch(
    "/{nroGrupo}/dia/{dia}/empleado",
    response_model=PerteneceResponse,
    summary="Actualizar empleado asignado a un grupo-día",
    response_description="Empleado actualizado exitosamente"
)
async def actualizar_empleado(
    nroGrupo: str,
    dia: str,
    empleado_data: UpdateEmpleadoGrupo,
    db: Connection = Depends(get_db)
):
    """
    Actualiza o asigna un empleado a un grupo en un día específico.
    
    - **nroGrupo**: Identificador del grupo
    - **dia**: Día de la semana
    - **dniEmpleado**: DNI del nuevo empleado asignado
    """
    # Para esta operación, necesitarías crear un servicio similar a actualizar_capacidad
    # o modificar el existente. Por ahora lo dejo como placeholder.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidad en desarrollo"
    )

# ELIMINAR relación grupo-día
@router.delete(
    "/{nroGrupo}/dia/{dia}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar relación grupo-día",
    response_description="Relación eliminada exitosamente"
)
async def eliminar_relacion(
    nroGrupo: str,
    dia: str,
    db: Connection = Depends(get_db)
):
    """
    Elimina la relación entre un grupo y un día específico.
    
    - **nroGrupo**: Identificador del grupo
    - **dia**: Día de la semana a desasignar
    """
    await eliminar_relacion_grupo_dia(conn=db, nroGrupo=nroGrupo, dia=dia)

# OBTENER días disponibles
@router.get(
    "/dias/disponibles",
    response_model=List[str],
    summary="Obtener lista de días disponibles",
    response_description="Lista de días configurados en el sistema"
)
async def obtener_dias_disponibles(
    db: Connection = Depends(get_db)
):
    """
    Obtiene la lista de todos los días de la semana configurados en el sistema.
    """
    dias = await db.fetch('SELECT dia FROM "Dia" ORDER BY dia')
    return [dia["dia"] for dia in dias]