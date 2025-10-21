
from asyncpg import Connection
from typing import List
from datetime import datetime

from schemas.reclamoSchema import (
    ReclamoCreate,
    ReclamoUpdate,
    ReclamoResponse
)
from utils.exceptions import (
    DatabaseException,
    NotFoundException,
    AuthorizationException
)

async def _verificar_propiedad_reclamo(conn: Connection, id_reclamo: int, dni_alumno: str):
    """Función interna para verificar si un reclamo pertenece al alumno."""
    propietario_dni = await conn.fetchval('SELECT dni FROM "Reclamo" WHERE "idReclamo" = $1', id_reclamo)
    if not propietario_dni:
        raise NotFoundException("Reclamo", id_reclamo)
    if propietario_dni != dni_alumno:
        raise AuthorizationException("No tiene permiso para modificar este reclamo.")
    return True

async def crear_reclamo(conn: Connection, reclamo: ReclamoCreate, dni_alumno: str) -> ReclamoResponse:
    try:
        ahora = datetime.now()
        query = """
        INSERT INTO "Reclamo" (comentario, fecha, hora, dni)
        VALUES ($1, $2, $3, $4)
        RETURNING "idReclamo", comentario, fecha, hora, dni
        """
        nuevo_reclamo = await conn.fetchrow(query, reclamo.comentario, ahora.date(), ahora.time(), dni_alumno)
        return ReclamoResponse(**dict(nuevo_reclamo))
    except Exception as e:
        raise DatabaseException("crear reclamo", str(e))

async def obtener_reclamos_por_alumno(conn: Connection, dni_alumno: str) -> List[ReclamoResponse]:
    try:
        query = 'SELECT * FROM "Reclamo" WHERE dni = $1 ORDER BY fecha DESC, hora DESC'
        reclamos = await conn.fetch(query, dni_alumno)
        return [ReclamoResponse(**dict(row)) for row in reclamos]
    except Exception as e:
        raise DatabaseException("obtener reclamos", str(e))

async def actualizar_reclamo(conn: Connection, id_reclamo: int, reclamo: ReclamoUpdate, dni_alumno: str) -> ReclamoResponse:
    try:
        await _verificar_propiedad_reclamo(conn, id_reclamo, dni_alumno)
        
        query = """
        UPDATE "Reclamo" SET comentario = $1
        WHERE "idReclamo" = $2
        RETURNING "idReclamo", comentario, fecha, hora, dni
        """
        reclamo_actualizado = await conn.fetchrow(query, reclamo.comentario, id_reclamo)
        return ReclamoResponse(**dict(reclamo_actualizado))
    except (DatabaseException, NotFoundException, AuthorizationException):
        raise
    except Exception as e:
        raise DatabaseException("actualizar reclamo", str(e))

async def eliminar_reclamo(conn: Connection, id_reclamo: int, dni_alumno: str):
    try:
        await _verificar_propiedad_reclamo(conn, id_reclamo, dni_alumno)
        
        result = await conn.execute('DELETE FROM "Reclamo" WHERE "idReclamo" = $1', id_reclamo)
        
        if result == "DELETE 0":
            raise NotFoundException("Reclamo", id_reclamo) # Por si se elimina entre la verificación y el borrado
    
    except (DatabaseException, NotFoundException, AuthorizationException):
        raise
    except Exception as e:
        raise DatabaseException("eliminar reclamo", str(e))

