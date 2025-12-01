
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db

from api.dependencies.security import alumno_required, admin_required

from schemas.reclamoSchema import (
    ReclamoCreate,
    ReclamoUpdate,
    ReclamoResponse,
    ReclamoListadoAdmin
)

from services import reclamoServices

router = APIRouter(
    prefix="/reclamos",
    tags=["Reclamos"]
)

# ==========================================
# RUTAS PARA ADMIN
# ==========================================

@router.get(
    "/",
    response_model=List[ReclamoListadoAdmin],
    summary="Listar todos los reclamos (Admin)",
    dependencies=[Depends(admin_required)] # <--- Protegido para Admin
)
async def listar_todos_los_reclamos(
    db: Connection = Depends(get_db)
):
    """
    Lista todos los reclamos registrados en el sistema con datos del alumno.
    """
    return await reclamoServices.listar_todos_reclamos(db)

# ==========================================
# RUTAS PARA ALUMNOS (Mis Reclamos)
# ==========================================

@router.post(
    "/",
    response_model=ReclamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo reclamo",
    dependencies=[Depends(alumno_required)] # <--- Protegido para Alumnos
)
async def crear_nuevo_reclamo(
    reclamo_data: ReclamoCreate,
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """Crea un nuevo reclamo para el alumno autenticado."""
    dni_alumno = current_user['dni']
    return await reclamoServices.crear_reclamo(db, reclamo_data, dni_alumno)

@router.get(
    "/mis-reclamos",
    response_model=List[ReclamoResponse],
    summary="Listar mis reclamos",
    dependencies=[Depends(alumno_required)] # <--- Protegido para Alumnos
)
async def listar_mis_reclamos(
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """Obtiene una lista de todos los reclamos realizados por el alumno autenticado."""
    dni_alumno = current_user['dni']
    return await reclamoServices.obtener_reclamos_por_alumno(db, dni_alumno)

@router.put(
    "/{id_reclamo}",
    response_model=ReclamoResponse,
    summary="Actualizar un reclamo",
    dependencies=[Depends(alumno_required)] # <--- Protegido para Alumnos
)
async def actualizar_un_reclamo(
    id_reclamo: int,
    reclamo_data: ReclamoUpdate,
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """Actualiza el comentario de un reclamo existente. Solo se puede actualizar un reclamo propio."""
    dni_alumno = current_user['dni']
    return await reclamoServices.actualizar_reclamo(db, id_reclamo, reclamo_data, dni_alumno)

@router.delete(
    "/{id_reclamo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un reclamo",
    dependencies=[Depends(alumno_required)] # <--- Protegido para Alumnos
)
async def eliminar_un_reclamo(
    id_reclamo: int,
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """Elimina un reclamo. Solo se puede eliminar un reclamo propio."""
    dni_alumno = current_user['dni']
    await reclamoServices.eliminar_reclamo(db, id_reclamo, dni_alumno)
    return

