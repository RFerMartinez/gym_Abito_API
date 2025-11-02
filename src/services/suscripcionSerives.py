import logging
from typing import List, Optional
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError

# --- Imports de Schemas (actualizados) ---
from schemas.suscripcionSchema import (
    SuscripcionCreate,
    SuscripcionResponse, # Usamos el nuevo schema de respuesta
    SuscripcionUpdate
)

# --- Imports de Excepciones Personalizadas ---
# (Asegúrate de que tu archivo utils/exceptions.py exista y las defina)
from utils.exceptions import (
    DatabaseException,
    DuplicateEntryException,
    NotFoundException,
    BusinessRuleException  # Usada para el error de FK
)

# SERVICE para crear una suscripcion nueva
async def create(
        con: Connection,
        suscripcion_data: SuscripcionCreate
) -> SuscripcionResponse: # <-- Cambiado a SuscripcionResponse
    """
    Crea una nueva suscripción en la base de datos.
    Lanza DuplicateEntryException si el nombre ya existe.
    """
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
        # Devolvemos el objeto completo usando el schema de respuesta
        return SuscripcionResponse(**suscripcion)
    
    except UniqueViolationError:
        # Error específico: La suscripción ya existe (HTTP 409)
        raise DuplicateEntryException("Suscripción", suscripcion_data.nombreSuscripcion)
    except Exception as e:
        # Error genérico (HTTP 500)
        logging.error(f"Error al crear suscripción: {e}")
        raise DatabaseException("crear suscripción", str(e))

# SERVICE para obtener todas las suscripciones
async def get_all(con: Connection) -> List[SuscripcionResponse]:
    """
    Obtiene una lista de todas las suscripciones.
    """
    try:
        query = """
            SELECT "nombreSuscripcion", precio
            FROM "Suscripcion"
            ORDER BY "nombreSuscripcion";
        """
        suscripciones = await con.fetch(query)
        return [SuscripcionResponse(**elem) for elem in suscripciones]
    except Exception as e:
        logging.error(f"Error al obtener suscripciones: {e}")
        raise DatabaseException("obtener suscripciones", str(e))

# SERVICE para actualizar el precio de una suscripcion
async def update_suscription_price(
        con: Connection,
        nombre_suscripcion: str,
        subs_data: SuscripcionUpdate
) -> SuscripcionResponse:
    """
    Actualiza el precio de una suscripción existente.
    Lanza NotFoundException si la suscripción no existe.
    """
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
            nombre_suscripcion
        )
        if not suscripcion:
            # Error específico: No encontrado (HTTP 404)
            raise NotFoundException("Suscripción", nombre_suscripcion)
        
        return SuscripcionResponse(**suscripcion)
    
    except NotFoundException:
        raise # Re-lanzamos la excepción 404 para que el handler la capture
    except Exception as e:
        logging.error(f"Error al actualizar suscripción: {e}")
        raise DatabaseException("actualizar suscripción", str(e))

# SERVICE para eliminar una suscripción
async def delete_subscription(con: Connection, nombre: str) -> None:
    """
    Elimina una suscripción por su nombre.
    Lanza NotFoundException si no existe.
    Lanza BusinessRuleException si está en uso (error de FK).
    """
    try:
        query = """
            DELETE FROM "Suscripcion"
            WHERE "nombreSuscripcion" = $1
            RETURNING "nombreSuscripcion";
        """
        res = await con.fetchrow(query, nombre)
        
        if not res:
            # Error específico: No encontrado (HTTP 404)
            raise NotFoundException("Suscripción", nombre)
        
        # Si tiene éxito, no devuelve nada (el endpoint dará 204 NO CONTENT)
        return
    
    except NotFoundException:
        raise # Re-lanzamos la excepción 404

    except ForeignKeyViolationError:
        # ¡ESTA ES LA MEJORA CLAVE! (HTTP 400 o 409)
        # Capturamos el error de FK y lo convertimos en una excepción
        # de regla de negocio con un mensaje claro.
        raise BusinessRuleException(
            "No se puede eliminar la suscripción porque está siendo utilizada por uno o más alumnos."
        )
    except Exception as e:
        logging.error(f"Error al eliminar suscripción: {e}")
        raise DatabaseException("eliminar suscripción", str(e))