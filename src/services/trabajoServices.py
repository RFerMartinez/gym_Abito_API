from typing import List
from fastapi import HTTPException, status
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError

# IMPORTS SCHEMAS
from schemas.trabajoSchema import (
    TrabajoCreate,
    UpdateTrabajoDescr,
    TrabajoInDB,
    TrabajoUpdate,
    TrabajoUpdateCompleto
)
from utils.exceptions import DatabaseException, DuplicateEntryException, NotFoundException

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
async def update_desc(con: Connection, nombreTrabajo: str, job_data: TrabajoUpdate) -> TrabajoInDB:
    """
    Actualiza la descripción de un trabajo existente.
    """
    try:
        query = """
            UPDATE "Trabajo"
            SET descripcion = $1
            WHERE "nombreTrabajo" = $2
            RETURNING "nombreTrabajo", descripcion;
        """
        job = await con.fetchrow(
            query,
            job_data.descripcion,
            nombreTrabajo
        )
        
        if not job:
            raise NotFoundException("Trabajo", nombreTrabajo)
            
        return TrabajoInDB(**job)
    except NotFoundException:
        raise # Re-lanzamos la excepción para que el handler la capture
    except Exception as e:
        raise DatabaseException("actualizar la descripción del trabajo", str(e))

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


# === SERVICIO REEMPLAZADO PARA ACTUALIZAR NOMBRE Y DESCRIPCIÓN ===
async def update_trabajo(con: Connection, old_job_name: str, job_data: TrabajoUpdateCompleto) -> TrabajoInDB:
    """
    Actualiza el nombre y la descripción de un trabajo existente de forma transaccional.
    """
    async with con.transaction():
        try:
            # 1. Verificar que el trabajo antiguo existe
            old_job = await con.fetchval('SELECT 1 FROM "Trabajo" WHERE "nombreTrabajo" = $1', old_job_name)
            if not old_job:
                raise NotFoundException("Trabajo", old_job_name)

            # Si el nombre no ha cambiado, es una simple actualización de descripción
            if old_job_name == job_data.nombreTrabajo:
                query = """
                    UPDATE "Trabajo" SET descripcion = $1
                    WHERE "nombreTrabajo" = $2
                    RETURNING "nombreTrabajo", descripcion;
                """
                updated_job = await con.fetchrow(query, job_data.descripcion, old_job_name)
                return TrabajoInDB(**updated_job)
            
            # Si el nombre ha cambiado, aplicamos la lógica de migración
            # 2. Insertar el nuevo trabajo (falla si el nuevo nombre ya existe)
            await con.execute(
                'INSERT INTO "Trabajo" ("nombreTrabajo", descripcion) VALUES ($1, $2)',
                job_data.nombreTrabajo, job_data.descripcion
            )
            
            # 3. Actualizar todas las referencias en la tabla Alumno
            await con.execute(
                'UPDATE "Alumno" SET "nombreTrabajo" = $1 WHERE "nombreTrabajo" = $2',
                job_data.nombreTrabajo, old_job_name
            )

            # 4. Actualizar todas las referencias en la tabla Cuota
            await con.execute(
                'UPDATE "Cuota" SET "nombreTrabajo" = $1 WHERE "nombreTrabajo" = $2',
                job_data.nombreTrabajo, old_job_name
            )
            
            # 5. Eliminar el trabajo antiguo
            await con.execute('DELETE FROM "Trabajo" WHERE "nombreTrabajo" = $1', old_job_name)
            
            return TrabajoInDB(**job_data.dict())

        except UniqueViolationError:
            raise DuplicateEntryException("nombreTrabajo", job_data.nombreTrabajo)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException("actualizar trabajo", str(e))