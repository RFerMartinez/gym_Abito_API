from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List, Annotated

from core.session import get_db
# Importamos dependencias de seguridad
from api.dependencies.auth import get_current_user 
from api.dependencies.security import staff_required

from schemas.avisoSchema import AvisoCreate, AvisoResponse, AvisoUpdate
from services import avisoServices

router = APIRouter(
    prefix="/avisos",
    tags=["Avisos"]
)

# === LECTURA (Público para usuarios logueados) ===
@router.get(
    "/",
    response_model=List[AvisoResponse],
    summary="Listar avisos",
    dependencies=[Depends(get_current_user)] 
)
async def listar_avisos(
    db: Connection = Depends(get_db)
):
    return await avisoServices.listar_avisos(db)

# === ESCRITURA (Solo Staff) ===
@router.post(
    "/",
    response_model=AvisoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo aviso (Staff)",
    description="El autor se asigna automáticamente según el usuario logueado."
)
async def crear_aviso(
    aviso: AvisoCreate,
    # staff_required devuelve el current_user si es válido
    current_user: dict = Depends(staff_required), 
    db: Connection = Depends(get_db)
):
    # Extraemos el DNI del usuario logueado (Admin o Empleado)
    dni_autor = current_user['dni']
    return await avisoServices.crear_aviso(db, aviso, dni_autor)

@router.put(
    "/{id_aviso}",
    response_model=AvisoResponse,
    summary="Actualizar texto de un aviso (Staff)",
    dependencies=[Depends(staff_required)]
)
async def actualizar_aviso(
    id_aviso: int,
    aviso: AvisoUpdate,
    db: Connection = Depends(get_db)
):
    return await avisoServices.actualizar_aviso(db, id_aviso, aviso)

@router.delete(
    "/{id_aviso}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un aviso (Staff)",
    dependencies=[Depends(staff_required)]
)
async def eliminar_aviso(
    id_aviso: int,
    db: Connection = Depends(get_db)
):
    await avisoServices.eliminar_aviso(db, id_aviso)
    return

