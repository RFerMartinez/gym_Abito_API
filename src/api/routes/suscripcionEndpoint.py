from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import Connection

from services.suscripcionSerives import (
    create,
    get_all,
    update_suscription_price,
    delete_subscription
)

from schemas.suscripcionSchema import (
    SuscripcionCreate,
    SuscripcionCreateResponse, 
    SuscripcionBase,
    SuscripcionUpdate,
    SuscripcionUpdatePrice
)

from typing import List
from core.session import get_db

# === DEPENDENCIA DE ADMIN ===
from api.dependencies.security import admin_required

router = APIRouter(prefix="/suscripciones", tags=["suscripciones"])

# CREAR SUSCRIPCIÓN
@router.post(
    "/", 
    response_model=SuscripcionCreateResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva suscripción (Admin)",
    dependencies=[Depends(admin_required)] # <--- Ruta protegida
)
async def crear_suscripcion(
    suscripcion: SuscripcionCreate,
    con: Connection = Depends(get_db)
):
    return await create(con, suscripcion)

# OBTENER TODAS LAS SUSCRIPCIONES (PÚBLICO)
@router.get(
    "/", 
    response_model=List[SuscripcionBase],
    summary="Obtener todas las suscripciones"
)
async def listar_suscripciones(con: Connection = Depends(get_db)):
    return await get_all(con)

# === ENDPOINT PATCH Y PROTEGIDO ===
@router.patch(
    "/{nombre_suscripcion}", 
    response_model=SuscripcionBase,
    summary="Actualizar el precio de una suscripción (Admin)",
    dependencies=[Depends(admin_required)] # <--- Ruta protegida
)
async def actualizar_precio_suscripcion(
    nombre_suscripcion: str, # <--- El nombre viene de la URL
    sub_data: SuscripcionUpdate, # <--- Usamos el nuevo esquema para el body
    con: Connection = Depends(get_db)
):
    return await update_suscription_price(con=con, nombre_suscripcion=nombre_suscripcion, subs_data=sub_data)

# ELIMINAR UNA SUSCRIPCION (PROTEGIDO)
@router.delete(
    "/{nombre_suscripcion}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una suscripción (Admin)",
    dependencies=[Depends(admin_required)] # <--- Ruta protegida
)
async def eliminar_suscripcion(
    nombre_suscripcion: str, # <--- Corregido para tomar el nombre de la URL
    con: Connection = Depends(get_db)
):
    await delete_subscription(con=con, nombre=nombre_suscripcion)
    return