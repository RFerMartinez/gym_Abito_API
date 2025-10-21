import logging

from typing import List, Optional
from fastapi import HTTPException
from  asyncpg import Connection

from schemas.suscripcionSchema import (
    SuscripcionCreate,
    SuscripcionCreateResponse,
    SuscripcionBase,
    SuscripcionUpdatePrice,
    SuscripcionUpdate
)

# SERVICE para crear una suscripcion nueva
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

# SERVICE para obtener todas las suscripciones
async def get_all(con: Connection) -> List[SuscripcionBase]:
    try:
        query = """
            SELECT "nombreSuscripcion", precio
            FROM "Suscripcion";
        """
        suscripciones = await con.fetch(query)
        return [SuscripcionBase(**elem)for elem in suscripciones]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al obtener suscripciones")

# SERVICE para actualizar el precio de una suscripcion
# === SERVICIO MODIFICADO PARA ACTUALIZAR PRECIO ===
async def update_suscription_price(
        con: Connection,
        nombre_suscripcion: str, # <--- Recibimos el nombre como argumento
        subs_data: SuscripcionUpdate # <--- Usamos el nuevo esquema
) -> SuscripcionBase:
    try:
        query = """
            UPDATE "Suscripcion"
            SET precio = $1
            WHERE "nombreSuscripcion" = $2
            RETURNING "nombreSuscripcion", precio;
        """
        suscripcion = await con.fetchrow(
            query,
            subs_data.precio,
            nombre_suscripcion) # <--- Usamos el nombre en el WHERE
        if not suscripcion:
            raise HTTPException(status_code=404, detail="Suscripción no encontrada")
        return SuscripcionBase(**suscripcion)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error al actualizar suscripcion")

# SERVICE para eliminar una suscripción
async def delete_subscription(con: Connection, nombre: str) -> dict:
    try:
        query = """
            DELETE FROM "Suscripcion"
            WHERE "nombreSuscripcion" = $1
            RETURNING "nombreSuscripcion";
        """
        res = await con.fetchrow(query, nombre)
        if not res:
            raise HTTPException(status_code=404, detail="Suscripción no encontrada")
        return {
            "message": "Suscripción eliminada correctamente"
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Error al elminar suscripción")

