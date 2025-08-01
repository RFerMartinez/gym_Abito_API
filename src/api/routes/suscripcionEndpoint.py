from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection
from services.suscripcionSerives import create
from schemas.suscripcionSchema import SuscripcionCreate, SuscripcionCreateResponse
from typing import List
from core.session import get_db

router = APIRouter(prefix="/suscripciones", tags=["suscripciones"])

@router.post("/", response_model=SuscripcionCreateResponse, status_code=201)
async def crear_suscripcion(
    suscripcion: SuscripcionCreate,
    con: Connection = Depends(get_db)
):
    return await create(con, suscripcion)

