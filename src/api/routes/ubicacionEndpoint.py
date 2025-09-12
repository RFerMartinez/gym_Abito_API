from fastapi import APIRouter, Depends, status, HTTPException
from asyncpg import Connection
from typing import List, Optional

from core.session import get_db

from schemas.ubicacionSchema import (
    ProvinciaCreate,
    ProvinciaResponse,
    LocalidadCreate,
    LocalidadResponse,
    ProvinciaConLocalidades,
)

from schemas.direccionSchema import (
    DireccionCreate,
    DireccionResponse,
    DireccionCompletaResponse
)

from services.ubicacionServices import (
    crear_provincia,
    obtener_provincias,
    crear_localidad,
    obtener_localidades_por_provincia,
    obtener_todas_localidades,
    obtener_localidades_agrupadas_por_provincia
)

from services.direccionServices import (
    crear_direccion,
    obtener_direccion_por_dni,
    actualizar_direccion,
    eliminar_direccion
)

router = APIRouter(
    prefix="/ubicacion",
    tags=["Ubicación"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_409_CONFLICT: {"description": "Conflicto - El recurso ya existe"}
    }
)

# ========== PROVINCIAS ==========

@router.post(
    "/provincias",
    response_model=ProvinciaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva provincia"
)
async def crear_nueva_provincia(
    provincia: ProvinciaCreate,
    db: Connection = Depends(get_db)
):
    return await crear_provincia(db, provincia)

@router.get(
    "/provincias",
    response_model=List[ProvinciaResponse],
    summary="Obtener todas las provincias"
)
async def listar_provincias(db: Connection = Depends(get_db)):
    return await obtener_provincias(db)

# ========== LOCALIDADES ==========

@router.post(
    "/localidades",
    response_model=LocalidadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva localidad"
)
async def crear_nueva_localidad(
    localidad: LocalidadCreate,
    db: Connection = Depends(get_db)
):
    return await crear_localidad(db, localidad)

@router.get(
    "/localidades",
    response_model=List[LocalidadResponse],
    summary="Obtener todas las localidades"
)
async def listar_localidades(db: Connection = Depends(get_db)):
    return await obtener_todas_localidades(db)

@router.get(
    "/provincias/{nomProvincia}/localidades",
    response_model=List[LocalidadResponse],
    summary="Obtener localidades por provincia"
)
async def obtener_localidades_provincia(
    nomProvincia: str,
    db: Connection = Depends(get_db)
):
    return await obtener_localidades_por_provincia(db, nomProvincia)

@router.get(
    "/provincias-localidades",
    response_model=List[ProvinciaConLocalidades],
    summary="Obtener localidades agrupadas por provincia"
)
async def obtener_localidades_agrupadas(db: Connection = Depends(get_db)):
    """
    Obtiene todas las localidades agrupadas por provincia en formato estructurado.
    
    Ejemplo de respuesta:
    [
        {
            "provincia": "Chaco",
            "localidades": ["Resistencia", "Barranqueras", "Fontana"]
        },
        {
            "provincia": "Santa Fe", 
            "localidades": ["Santa Fe", "Rosario"]
        }
    ]
    """
    return await obtener_localidades_agrupadas_por_provincia(db)
# ========== DIRECCIONES ==========

@router.post(
    "/direcciones",
    response_model=DireccionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva dirección"
)
async def crear_nueva_direccion(
    direccion: DireccionCreate,
    db: Connection = Depends(get_db)
):
    return await crear_direccion(db, direccion)

@router.get(
    "/direcciones/{dni}",
    response_model=DireccionCompletaResponse,
    summary="Obtener dirección por DNI"
)
async def obtener_direccion(
    dni: str,
    db: Connection = Depends(get_db)
):
    direccion = await obtener_direccion_por_dni(db, dni)
    if not direccion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró dirección para el DNI: {dni}"
        )
    return direccion

@router.put(
    "/direcciones/{dni}",
    response_model=DireccionResponse,
    summary="Actualizar dirección por DNI"
)
async def actualizar_direccion_existente(
    dni: str,
    direccion: DireccionCreate,
    db: Connection = Depends(get_db)
):
    return await actualizar_direccion(db, dni, direccion)

@router.delete(
    "/direcciones/{dni}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar dirección por DNI"
)
async def eliminar_direccion_existente(
    dni: str,
    db: Connection = Depends(get_db)
):
    success = await eliminar_direccion(db, dni)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró dirección para el DNI: {dni}"
        )