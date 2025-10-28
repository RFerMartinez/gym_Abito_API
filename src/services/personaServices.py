# src/services/personaServices.py
from asyncpg import Connection
from typing import List, Optional

from schemas.personaSchema import PersonaListado, PersonaDetalle
from utils.exceptions import DatabaseException, NotFoundException

async def listar_personas(conn: Connection) -> List[PersonaListado]:
    """
    Obtiene un listado de personas que NO SON Alumnos, NO SON Empleados
    y NO SON Administradores.
    """
    try:
        # Modificación: Añadimos exclusión de Empleados (e.dni IS NULL)
        # y de Administradores (p."esAdmin" = FALSE).
        query = """
        SELECT
            p.dni,
            p.nombre,
            p.apellido
        FROM "Persona" p
        LEFT JOIN "Alumno" a ON p.dni = a.dni
        LEFT JOIN "Empleado" e ON p.dni = e.dni
        WHERE a.dni IS NULL
            AND e.dni IS NULL
            AND p."esAdmin" = FALSE
        ORDER BY p.apellido, p.nombre;
        """
        personas = await conn.fetch(query)
        return [PersonaListado(**dict(row)) for row in personas]
    except Exception as e:
        raise DatabaseException("listar personas", str(e))


async def obtener_persona_por_dni(conn: Connection, dni: str) -> PersonaDetalle:
    """
    Obtiene los detalles de una persona, SOLO SI NO ES Alumno,
    NO ES Empleado y NO ES Administrador.
    """
    try:
        # Modificación: Añadimos las nuevas condiciones al WHERE.
        query = """
        SELECT
            p.dni,
            p.nombre,
            p.apellido,
            p.telefono,
            p.email,
            p.usuario,
            p."requiereCambioClave",
            p."esAdmin",
            p.sexo,
            d."nomLocalidad" as localidad,
            d."nomProvincia" as provincia,
            d.calle as "Calle",
            d.numero as nro,
            FALSE as es_alumno, -- Garantizado por el WHERE
            FALSE as es_empleado -- Garantizado por el WHERE
        FROM "Persona" p
        INNER JOIN "Direccion" d ON p.dni = d.dni
        WHERE p.dni = $1
            AND p."esAdmin" = FALSE
            AND NOT EXISTS (SELECT 1 FROM "Alumno" a WHERE a.dni = p.dni)
            AND NOT EXISTS (SELECT 1 FROM "Empleado" e WHERE e.dni = p.dni);
        """
        
        persona_data = await conn.fetchrow(query, dni)
        
        if not persona_data:
            raise NotFoundException("Persona", dni)
        
        return PersonaDetalle(**dict(persona_data))
        
    except NotFoundException:
        raise # Re-lanzar la excepción para que el endpoint la maneje
    except Exception as e:
        raise DatabaseException("obtener detalle de persona", str(e))

