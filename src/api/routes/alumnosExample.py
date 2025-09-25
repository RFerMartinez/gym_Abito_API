from fastapi import APIRouter, Depends
from asyncpg import Connection
from api.dependencies.security import alumno_activo_required, alumno_required
from core.session import get_db

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])

@router.get("/mi-horario")
async def mi_horario(
    current_user: dict = Depends(alumno_activo_required)  # Solo alumnos activos
):
    """Solo alumnos activos pueden ver su horario"""
    return {"message": "Horario del alumno", "user": current_user}

@router.get("/mi-perfil")
async def perfil_alumno(
    current_user: dict = Depends(alumno_required)  # Cualquier alumno
):
    """Cualquier alumno (activo o inactivo) puede ver su perfil"""
    return current_user