from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection
from services.suscripcionSerives import create, get_all, update_suscription_price, delete_subscription
from schemas.suscripcionSchema import (
    SuscripcionCreate,
    SuscripcionCreateResponse, 
    SuscripcionBase,
    SuscripcionUpdatePrice)
from typing import List
from core.session import get_db

router = APIRouter(prefix="/suscripciones", tags=["suscripciones"])

# CREAR SSUCRIPCIÓN
@router.post("/", response_model=SuscripcionCreateResponse, status_code=201)
async def crear_suscripcion(
    suscripcion: SuscripcionCreate,
    con: Connection = Depends(get_db)
):
    return await create(con, suscripcion)

# OBTENER TODAS LAS SUSCRIPCIONES
@router.get("/", response_model=List[SuscripcionBase])
async def listar_suscripciones(con: Connection = Depends(get_db)):
    return await get_all(con)

# ACTUALIZAR PRECIO DE UNA SUSCRIPCION
@router.put("/{nameSub}")
async def actualizar_precio_suscripcion(
    sub: SuscripcionUpdatePrice,
    con: Connection = Depends(get_db)
):
    return await update_suscription_price(con=con, subs_data=sub)

# ELIMINAR UNA SUSCRIPCION
@router.delete("/{nameSub}")
async def eliminar_suscripcion(nombreSuscripcion: str, con: Connection = Depends(get_db)):
    return await delete_subscription(con=con, nombre=nombreSuscripcion)