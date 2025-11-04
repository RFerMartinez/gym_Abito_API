# src/services/personaServices.py
from asyncpg import Connection, ForeignKeyViolationError
from typing import List, Optional

from schemas.personaSchema import (
    PersonaListado,
    PersonaDetalle
)

from utils.exceptions import (
    DatabaseException,
    NotFoundException,
    BusinessRuleException
)

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
            d.calle,
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

async def eliminar_persona(conn: Connection, dni: str) -> None:
    """
    Elimina una persona, SOLO SI NO ES Alumno, NO ES Empleado
    y NO ES Administrador.
    """
    async with conn.transaction():
        try:
            # 1. Verificar que la persona existe y obtener su estado de admin
            persona_data = await conn.fetchrow(
                'SELECT "esAdmin" FROM "Persona" WHERE dni = $1', dni
            )
            
            if not persona_data:
                raise NotFoundException("Persona", dni)

            # 2. Validar reglas de negocio (no eliminar roles protegidos)
            if persona_data["esAdmin"]:
                raise BusinessRuleException("No se puede eliminar a un administrador.")
            
            es_alumno = await conn.fetchval('SELECT 1 FROM "Alumno" WHERE dni = $1', dni)
            if es_alumno:
                raise BusinessRuleException("Esta persona es un Alumno. No se puede eliminar.")

            es_empleado = await conn.fetchval('SELECT 1 FROM "Empleado" WHERE dni = $1', dni)
            if es_empleado:
                raise BusinessRuleException("Esta persona es un Empleado. No se puede eliminar.")

            # 3. Proceder con la eliminación de dependencias
            # (Asumimos que solo "Direccion" está ligada a una persona "simple")
            await conn.execute('DELETE FROM "Direccion" WHERE dni = $1', dni)
            
            # 4. Eliminar la persona
            result = await conn.execute('DELETE FROM "Persona" WHERE dni = $1', dni)

            if result == "DELETE 0":
                # Fallback por si acaso, aunque la primera query ya lo valida
                raise NotFoundException("Persona", dni)

        except (NotFoundException, BusinessRuleException):
            raise # Re-lanzar excepciones de negocio
        except ForeignKeyViolationError as e:
            # Error de seguridad por si se nos olvida borrar una dependencia
            raise BusinessRuleException(f"Error de integridad: La persona tiene otros datos asociados. Detalle: {e.detail}")
        except Exception as e:
            raise DatabaseException("eliminar persona", str(e))

