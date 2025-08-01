import logging

from typing import List, Optional
from fastapi import HTTPException
from  asyncpg import Connection

from schemas.suscripcionSchema import SuscripcionCreate, SuscripcionCreateResponse

# SERVICE para crear una suscripcion nueba
async def create(
        con: Connection,
        suscripcion_data: SuscripcionCreate
) -> SuscripcionCreateResponse:
    try:
        query = """
            INSERT INTO "Suscripcion" ("nombreSuscripcion", precio)
            VALUES ($1, $2)
            RETURNING "nombreSuscripcion", precio;
        """
        suscripcion = await con.fetchrow(
            query,
            suscripcion_data.nombreSuscripcion,
            suscripcion_data.precio
        )
        return SuscripcionCreateResponse(**suscripcion)
    except Exception as e:
        if "duplicate key" in str(e):
            raise HTTPException(status_code=400, detail="La suscripción ya existe")
        raise HTTPException(status_code=500, detail="Error al crear suscripción")

