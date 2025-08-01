from typing import List
from fastapi import HTTPException, status
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError

# IMPORTS SCHEMAS
from schemas.trabajoSchema import (
    TrabajoCreate,
    UpdateTrabajoDescr,
    TrabajoInDB
)

# SERVICE para crear un trabajo nuevo
async def create(con: Connection, job_data: TrabajoCreate) -> TrabajoInDB:
    try:
        query = """
            INSERT INTO "Trabajo" ("nombreTrabajo", descripcion)
            VALUES ($1, $2)
            RETURNING "nombreTrabajo", descripcion;
        """
        job = await con.fetchrow(
            query,
            job_data.nombreTrabajo,
            job_data.descripcion
        )
        return TrabajoInDB(**job)
    except UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El trabajo '{job_data.nombreTrabajo}' ya existe"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al crear trabajo: {str(e)}"
        )

# SERVICE para obtener todos los trabajos
async def get_all(con: Connection) -> List[TrabajoInDB]:
    try:
        query = """
            SELECT * FROM "Trabajo";
        """
        res = await con.fetch(query)
        return [TrabajoInDB(**elem) for elem in res]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al listar los trabajos: {str(e)}"
        )

# Service para actualizar la descripcion de un trabajo
async def update_desc(con: Connection, job_data: UpdateTrabajoDescr) -> TrabajoInDB:
    try:
        pass
    except Exception as e:
        pass

# Service para eliminar un trabajo
async def delete(con: Connection, nombreTrabajo: str) -> dict:
    try:
        query = """
            DELETE FROM "Trabajo"
            WHERE "nombreTrabajo" = $1
            RETURNING "nombreTrabajo";
        """
        res = await con.fetchrow(query, nombreTrabajo)
        
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trabajo '{nombreTrabajo}' no encontrado"
            )
            
        return {
            "message": f"El trabajo '{nombreTrabajo}' se eliminó correctamente"
        }
    except ForeignKeyViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el trabajo porque tiene registros asociados"
        )
    except HTTPException:
        raise  # Re-lanza las HTTPException que ya hemos capturado
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar trabajo: {str(e)}"
        )


