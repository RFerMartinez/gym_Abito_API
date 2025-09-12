from asyncpg import Connection
from typing import List, Optional
from schemas.ubicacionSchema import (
    ProvinciaCreate,
    ProvinciaResponse,
    LocalidadCreate, 
    LocalidadResponse,
    ProvinciaConLocalidades
)
from utils.exceptions import NotFoundException, DatabaseException, DuplicateEntryException

async def crear_provincia(conn: Connection, provincia: ProvinciaCreate) -> ProvinciaResponse:
    try:
        query = '''
        INSERT INTO "Provincia" ("nomProvincia")
        VALUES ($1)
        RETURNING "nomProvincia"
        '''
        result = await conn.fetchrow(query, provincia.nomProvincia)
        return ProvinciaResponse(**result)
    except Exception as e:
        raise DatabaseException("crear provincia", str(e))

async def obtener_provincias(conn: Connection) -> List[ProvinciaResponse]:
    try:
        query = 'SELECT "nomProvincia" FROM "Provincia" ORDER BY "nomProvincia"'
        resultados = await conn.fetch(query)
        return [ProvinciaResponse(**dict(row)) for row in resultados]
    except Exception as e:
        raise DatabaseException("obtener provincias", str(e))

async def crear_localidad(conn: Connection, localidad: LocalidadCreate) -> LocalidadResponse:
    try:
        # Verificar que la provincia existe
        provincia_exists = await conn.fetchval(
            'SELECT 1 FROM "Provincia" WHERE "nomProvincia" = $1',
            localidad.nomProvincia
        )
        if not provincia_exists:
            raise NotFoundException("Provincia", localidad.nomProvincia)

        query = '''
        INSERT INTO "Localidad" ("nomLocalidad", "nomProvincia")
        VALUES ($1, $2)
        RETURNING "nomLocalidad", "nomProvincia"
        '''
        result = await conn.fetchrow(query, localidad.nomLocalidad, localidad.nomProvincia)
        return LocalidadResponse(**result)
    except Exception as e:
        raise DatabaseException("crear localidad", str(e))

async def obtener_localidades_por_provincia(conn: Connection, nomProvincia: str) -> List[LocalidadResponse]:
    try:
        query = '''
        SELECT "nomLocalidad", "nomProvincia" 
        FROM "Localidad" 
        WHERE "nomProvincia" = $1 
        ORDER BY "nomLocalidad"
        '''
        resultados = await conn.fetch(query, nomProvincia)
        return [LocalidadResponse(**dict(row)) for row in resultados]
    except Exception as e:
        raise DatabaseException("obtener localidades por provincia", str(e))

async def obtener_todas_localidades(conn: Connection) -> List[LocalidadResponse]:
    try:
        query = '''
        SELECT "nomLocalidad", "nomProvincia" 
        FROM "Localidad" 
        ORDER BY "nomProvincia", "nomLocalidad"
        '''
        resultados = await conn.fetch(query)
        return [LocalidadResponse(**dict(row)) for row in resultados]
    except Exception as e:
        raise DatabaseException("obtener todas las localidades", str(e))

async def obtener_localidades_agrupadas_por_provincia(conn: Connection) -> List[ProvinciaConLocalidades]:
    """
    Obtiene todas las localidades agrupadas por provincia
    """
    try:
        query = '''
        SELECT 
            p."nomProvincia" as provincia,
            ARRAY_AGG(l."nomLocalidad" ORDER BY l."nomLocalidad") as localidades
        FROM "Provincia" p
        LEFT JOIN "Localidad" l ON p."nomProvincia" = l."nomProvincia"
        GROUP BY p."nomProvincia"
        ORDER BY p."nomProvincia"
        '''
        
        resultados = await conn.fetch(query)
        
        provincias_con_localidades = []
        for row in resultados:
            provincia_data = {
                "provincia": row["provincia"],
                "localidades": row["localidades"] or []  # Asegurar lista vacía si no hay localidades
            }
            provincias_con_localidades.append(ProvinciaConLocalidades(**provincia_data))
        
        return provincias_con_localidades
        
    except Exception as e:
        raise DatabaseException("obtener localidades agrupadas por provincia", str(e))