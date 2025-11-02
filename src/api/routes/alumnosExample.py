from fastapi import APIRouter, Depends
from asyncpg import Connection

from api.dependencies.security import (
    alumno_activo_required,
    alumno_required
)

from core.session import get_db

from schemas.alumnoSchema import (
    AlumnoDetalleParaAlumno,
    HorariosAlumnoResponse
)

from services.alumnoServices import (
    obtener_detalle_alumno_auth,
    obtener_horarios_alumno
)

router = APIRouter(
    prefix="/alumnos",
    tags=["Alumnos"]
)

@router.get(
    "/mi-horario",
    response_model=HorariosAlumnoResponse,
    summary="Obtener los horarios del alumno auth. Usar en MisHorarios.vue (Alumno)"
)
async def mi_horario(
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """Solo alumnos activos pueden ver su horario"""
    dni_alumno = current_user['dni']
    lista_horarios = await obtener_horarios_alumno(conn=db, dni=dni_alumno)
    return {"horarios": lista_horarios}


@router.get(
    "/mi-perfil",
    response_model=AlumnoDetalleParaAlumno,
    summary="Obtener datos del alumno auth. Usar en infoAlumno.vue (Alumno)"
)
async def perfil_alumno(
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """
    Cualquier alumno (activo o inactivo) puede ver su perfil detallado.
    """
    # <-- CAMBIO: Obtener DNI y llamar al servicio
    dni_alumno = current_user['dni']
    # Reutilizamos el servicio que ya obtiene todos los detalles
    return await obtener_detalle_alumno_auth(conn=db, dni=dni_alumno)