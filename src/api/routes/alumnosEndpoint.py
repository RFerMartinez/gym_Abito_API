# src/api/routes/alumnosEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from core.session import get_db
from schemas.alumnoSchema import AlumnoActivate, AlumnoActivateResponse
from services.alumnoServices import activar_alumno
from api.dependencies.security import staff_required

router = APIRouter(
    prefix="/alumnos", 
    tags=["Alumnos"],
    dependencies=[Depends(staff_required)] # Proteger todas las rutas de este router
)

@router.post(
    "/activar",
    response_model=AlumnoActivateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activar un nuevo alumno",
    response_description="El alumno ha sido activado y asignado a sus horarios."
)
async def activar_nuevo_alumno(
    data: AlumnoActivate,
    db: Connection = Depends(get_db)
):
    """
    Endpoint para activar una persona como alumno activo en el sistema.

    - **dni**: DNI de una persona ya registrada.
    - **sexo**: 'M' o 'F'.
    - **nombreTrabajo**: Un trabajo que ya exista en la base de datos.
    - **nombreSuscripcion**: Una suscripción existente.
    - **horarios**: Una lista con los grupos y días a los que asistirá el alumno.
    
    Requiere permisos de **staff (administrador o empleado)**.
    """
    return await activar_alumno(conn=db, data=data)