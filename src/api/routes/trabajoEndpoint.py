from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

# SESSION
from core.session import get_db

# SERVICES
from services.trabajoServices import (
    create,
    get_all,
    delete,
    update_desc,
    update_trabajo
)

# SCHEMAS
from schemas.trabajoSchema import (
    TrabajoCreate,
    UpdateTrabajoDescr,
    TrabajoInDB,
    TrabajoUpdate,
    TrabajoUpdateCompleto
)

# DEPENDENCIA DE ADMIN
from api.dependencies.security import admin_required

# BLUEPRINT de /trabajo
router = APIRouter(
    prefix="/trabajo",
    tags=["Trabajos"],
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
    response_description="El trabajo fue creado",
    dependencies=[Depends(admin_required)] # <-- Solo admin puede crear trabajos
)
async def crear_trabajo(
    job_data: TrabajoCreate,
    db: Connection = Depends(get_db)
):
    return await create(con=db, job_data=job_data)

# LISTAR todos los trabajos - RUTA PÚBLICA
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
    path="/{nombreTrabajo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un trabajo",
    response_description="Trabajo eliminado",
    dependencies=[Depends(admin_required)] # <-- Solo admin puede eliminar trabajos
)
async def eliminar_trabajo(
    nombreTrabajo: str,
    db: Connection = Depends(get_db)
):
    await delete(db, nombreTrabajo)

# === NUEVO ENDPOINT PARA ACTUALIZAR UN TRABAJO (PROTEGIDO) ===
@router.patch(
    "/{jobName}",
    response_model=TrabajoInDB,
    summary="Actualizar la descripción de unn trabajo (Admin)",
    response_description="El trabajo fue actualizado exitosamente",
    dependencies=[Depends(admin_required)] # <--- Ruta protegida para admins
)
async def actualizar_trabajo(
    jobName: str,
    job_data: TrabajoUpdate,
    db: Connection = Depends(get_db)
):
    """
    Actualiza la descripción de un trabajo existente.
    **Requiere permisos de administrador.**
    """
    return await update_desc(db, jobName, job_data)


# === ENDPOINT PUT MODIFICADO ===
@router.put(
    "/{jobName}",
    response_model=TrabajoInDB,
    summary="Actualizar un trabajo (Admin)",
    response_description="El trabajo fue actualizado exitosamente",
    dependencies=[Depends(admin_required)]
)
async def actualizar_trabajo_completo(
    jobName: str,
    job_data: TrabajoUpdateCompleto, # <--- Usamos el nuevo esquema en el body
    db: Connection = Depends(get_db)
):
    """
    Actualiza el nombre y/o la descripción de un trabajo existente.
    Si se cambia el nombre, todas las referencias se migrarán al nuevo.
    **Requiere permisos de administrador.**
    """
    return await update_trabajo(db, jobName, job_data) # <--- Llamamos al nuevo servicio