from asyncpg import Connection
from typing import List, Optional
from schemas.direccionSchema import DireccionCreate, DireccionResponse, DireccionCompletaResponse
from utils.exceptions import NotFoundException, DatabaseException

async def crear_direccion(conn: Connection, direccion: DireccionCreate) -> DireccionResponse:
    try:
        # Verificar que la localidad existe en la provincia
        localidad_exists = await conn.fetchval('''
            SELECT 1 FROM "Localidad" 
            WHERE "nomLocalidad" = $1 AND "nomProvincia" = $2
        ''', direccion.nomLocalidad, direccion.nomProvincia)
        
        if not localidad_exists:
            raise NotFoundException("Localidad/Provincia",
                                    f"{direccion.nomLocalidad}/{direccion.nomProvincia}")

        query = '''
        INSERT INTO "Direccion" 
            ("nomLocalidad", "nomProvincia", numero, calle, dni)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING "idDireccion", "nomLocalidad", "nomProvincia", numero, calle, dni
        '''
        
        result = await conn.fetchrow(
            query,
            direccion.nomLocalidad,
            direccion.nomProvincia,
            direccion.numero,
            direccion.calle,
            direccion.dni
        )
        return DireccionResponse(**result)
    except Exception as e:
        raise DatabaseException("crear dirección", str(e))

async def obtener_direccion_por_dni(conn: Connection, dni: str) -> Optional[DireccionCompletaResponse]:
    """
    Obtiene dirección por DNI con nombres planos (no objetos anidados)
    """
    try:
        query = '''
        SELECT 
            d."idDireccion",
            d."nomLocalidad",
            d."nomProvincia", 
            d.numero,
            d.calle,
            d.dni,
            l."nomLocalidad" as nombre_localidad,
            p."nomProvincia" as nombre_provincia
        FROM "Direccion" d
        JOIN "Localidad" l ON d."nomLocalidad" = l."nomLocalidad" AND d."nomProvincia" = l."nomProvincia"
        JOIN "Provincia" p ON l."nomProvincia" = p."nomProvincia"
        WHERE d.dni = $1
        '''
        
        result = await conn.fetchrow(query, dni)
        if not result:
            return None
        
        # Convertir a diccionario y mapear a la respuesta plana
        direccion_dict = dict(result)
        direccion_data = {
            "idDireccion": direccion_dict["idDireccion"],
            "nomLocalidad": direccion_dict["nomLocalidad"],
            "nomProvincia": direccion_dict["nomProvincia"],
            "numero": direccion_dict["numero"],
            "calle": direccion_dict["calle"],
            "dni": direccion_dict["dni"],
            "nombre_localidad": direccion_dict["nombre_localidad"],
            "nombre_provincia": direccion_dict["nombre_provincia"]
        }
            
        return DireccionCompletaResponse(**direccion_data)
    except Exception as e:
        raise DatabaseException("obtener dirección por DNI", str(e))

async def actualizar_direccion(conn: Connection, dni: str, direccion: DireccionCreate) -> DireccionResponse:
    try:
        # Verificar que la localidad existe
        localidad_exists = await conn.fetchval('''
            SELECT 1 FROM "Localidad" 
            WHERE "nomLocalidad" = $1 AND "nomProvincia" = $2
        ''', direccion.nomLocalidad, direccion.nomProvincia)
        
        if not localidad_exists:
            raise NotFoundException("Localidad/Provincia",
                                    f"{direccion.nomLocalidad}/{direccion.nomProvincia}")

        query = '''
        UPDATE "Direccion" 
        SET "nomLocalidad" = $1, "nomProvincia" = $2, numero = $3, calle = $4
        WHERE dni = $5
        RETURNING "idDireccion", "nomLocalidad", "nomProvincia", numero, calle, dni
        '''
        
        result = await conn.fetchrow(
            query,
            direccion.nomLocalidad,
            direccion.nomProvincia,
            direccion.numero,
            direccion.calle,
            dni
        )
        
        if not result:
            raise NotFoundException("Dirección", dni)
            
        return DireccionResponse(**result)
    except Exception as e:
        raise DatabaseException("actualizar dirección", str(e))

async def eliminar_direccion(conn: Connection, dni: str) -> bool:
    try:
        result = await conn.execute('DELETE FROM "Direccion" WHERE dni = $1', dni)
        return result == "DELETE 1"
    except Exception as e:
        raise DatabaseException("eliminar dirección", str(e))