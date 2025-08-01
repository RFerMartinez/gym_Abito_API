from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

# SESSION
from core.session import get_db

# SERVICES
from services.trabajoServices import (
    create,
    get_all,
    delete
)

# SCHEMAS
from schemas.trabajoSchema import (
    TrabajoCreate,
    UpdateTrabajoDescr,
    TrabajoInDB
)

# BLUEPRINT de /trabajo
router = APIRouter(
    prefix="/trabajo",
    tags=["trabajos"],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Trabajo no encontrado"
        },
        status.HTTP_409_CONFLICT: {
            "description": "Conflicto - El trabajo ya existe"
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Error en la consulta - ErrorForeignKey"
        }
    }
)

# ===============================================================

# CREAR trabajo
@router.post(
    "/",
    response_model=TrabajoInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un trabajo nuevo",
    response_description="El trabajo fue creado"
)
async def crear_trabajo(
    job_data: TrabajoCreate,
    db: Connection = Depends(get_db)
):
    return await create(con=db, job_data=job_data)

# LISTAR todos los trabajos
@router.get(
    path="/",
    response_model=List[TrabajoInDB],
    summary="Listar todos los trabajos",
    response_description="Lista de todos los trabajos"
)
async def listar_trabajos(
    db: Connection = Depends(get_db)
):
    return await get_all(con=db)

@router.delete(
    path="/{jobName}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un trabajo",
    response_description="Trabajo eliminado"
)
async def eliminar_trabajo(
    nombreTrabajo: str,
    db: Connection = Depends(get_db)
):
    await delete(db, nombreTrabajo)



