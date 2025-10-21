
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db

from api.dependencies.security import alumno_required

from schemas.reclamoSchema import (
    ReclamoCreate,
    ReclamoUpdate,
    ReclamoResponse
)

from services import reclamoServices

router = APIRouter(
    prefix="/reclamos",
    tags=["Reclamos"],
    dependencies=[Depends(alumno_required)] # <-- ¡Protegido para alumnos!
)

@router.post(
    "/",
    response_model=ReclamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo reclamo"
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
    summary="Listar mis reclamos"
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
    summary="Actualizar un reclamo"
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
    summary="Eliminar un reclamo"
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

