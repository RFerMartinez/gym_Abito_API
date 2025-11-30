from asyncpg import Connection
from typing import List

from schemas.avisoSchema import AvisoCreate, AvisoUpdate, AvisoResponse
from utils.exceptions import DatabaseException, NotFoundException

async def crear_aviso(conn: Connection, aviso: AvisoCreate, dni_autor: str) -> AvisoResponse:
    """
    Crea un aviso. La fecha y hora se generan automáticamente en la BD.
    """
    try:
        # Validamos que el autor exista (por integridad, aunque el token ya lo asegura)
        # No es estrictamente necesario si confiamos en el token, pero es buena práctica.
        
        query = """
        INSERT INTO "Aviso" (descripcion, dni)
        VALUES ($1, $2)
        RETURNING "idAviso", descripcion, fecha, hora, dni
        """
        # Solo pasamos descripción y DNI. La BD pone fecha y hora.
        res = await conn.fetchrow(query, aviso.descripcion, dni_autor)
        return AvisoResponse(**dict(res))
    except Exception as e:
        raise DatabaseException("crear aviso", str(e))

async def listar_avisos(conn: Connection) -> List[AvisoResponse]:
    """
    Lista avisos. Podrías hacer un JOIN con Persona para traer el nombre del autor si quisieras.
    """
    try:
        query = """
        SELECT "idAviso", descripcion, fecha, hora, dni
        FROM "Aviso"
        ORDER BY fecha DESC, hora DESC
        """
        res = await conn.fetch(query)
        return [AvisoResponse(**dict(row)) for row in res]
    except Exception as e:
        raise DatabaseException("listar avisos", str(e))

async def actualizar_aviso(conn: Connection, id_aviso: int, aviso: AvisoUpdate) -> AvisoResponse:
    """
    Actualiza SOLO la descripción del aviso.
    """
    try:
        # 1. Verificar existencia
        exists = await conn.fetchval('SELECT 1 FROM "Aviso" WHERE "idAviso" = $1', id_aviso)
        if not exists:
            raise NotFoundException("Aviso", id_aviso)

        # 2. Actualizar
        query = """
            UPDATE "Aviso"
            SET descripcion = $1
            WHERE "idAviso" = $2
            RETURNING "idAviso", descripcion, fecha, hora, dni
        """
        
        res = await conn.fetchrow(query, aviso.descripcion, id_aviso)
        return AvisoResponse(**dict(res))

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("actualizar aviso", str(e))

async def eliminar_aviso(conn: Connection, id_aviso: int) -> None:
    # (Este se mantiene igual)
    try:
        res = await conn.execute('DELETE FROM "Aviso" WHERE "idAviso" = $1', id_aviso)
        if res == "DELETE 0":
            raise NotFoundException("Aviso", id_aviso)
    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("eliminar aviso", str(e))

