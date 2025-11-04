# src/api/routes/personaEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from api.dependencies.security import staff_required, admin_required
from schemas.personaSchema import PersonaListado, PersonaDetalle
from services import personaServices

router = APIRouter(
    prefix="/personas",
    tags=["Personas"],
    dependencies=[Depends(staff_required)] # <-- ¡Protegemos todas las rutas de este archivo!
)

@router.get(
    "/",
    response_model=List[PersonaListado],
    summary="Listar todas las personas (Staff)",
    response_description="Lista de DNI, Nombre y Apellido de todas las personas"
)
async def get_lista_personas(
    db: Connection = Depends(get_db)
):
    """
    Obtiene una lista simple de todas las personas registradas en el sistema.
    
    Requiere permisos de **staff (administrador o empleado)**.
    """
    return await personaServices.listar_personas(conn=db)

@router.get(
    "/{dni}",
    response_model=PersonaDetalle,
    summary="Obtener detalles de una persona (Staff)",
    response_description="Información detallada de la persona"
)
async def get_persona_detalle(
    dni: str,
    db: Connection = Depends(get_db)
):
    """
    Obtiene la información detallada de una persona por su DNI.
    No incluye la contraseña.
    
    Requiere permisos de **staff (administrador o empleado)**.
    """
    return await personaServices.obtener_persona_por_dni(conn=db, dni=dni)

@router.delete(
    "/{dni}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una persona (Solo Admin)",
    response_description="Persona eliminada exitosamente",
    dependencies=[Depends(admin_required)] # <-- Sobrescribe a 'staff' y exige ADMIN
)
async def delete_persona(
    dni: str,
    db: Connection = Depends(get_db)
):
    """
    Elimina una persona del sistema, SOLO SI NO ES Alumno,
    NO ES Empleado y NO ES Administrador.
    
    Esta operación es destructiva y eliminará también la dirección
    asociada a esta persona.
    
    Requiere permisos de **administrador**.
    """
    await personaServices.eliminar_persona(conn=db, dni=dni)
    return # Devuelve 204 No Content

