# src/api/routes/alumnosEndpoint.py
from fastapi import APIRouter, Depends, status, Body
from asyncpg import Connection
from typing import List

from core.session import get_db

from schemas.alumnoSchema import (
    AlumnoActivate,
    AlumnoActivateResponse,
    AlumnoListado,
    AlumnoDetalle,
    HorarioAlumno,
    HorariosAlumnoResponse,
    HorariosUpdate,
    AlumnoPerfilUpdate,
    AlumnoPlanUpdate
)
from services.alumnoServices import (
    activar_alumno,
    listar_alumnos_detalle,
    obtener_detalle_alumno,
    obtener_horarios_alumno,
    actualizar_horarios_alumno,
    actualizar_perfil_alumno,
    actualizar_plan_alumno,
    eliminar_alumno
)
from api.dependencies.security import (
    staff_required,
    admin_required
)

router = APIRouter(
    prefix="/alumnos", 
    tags=["Alumnos"],
)

@router.post(
    "/activar",
    response_model=AlumnoActivateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activar un nuevo alumno",
    response_description="El alumno ha sido activado y asignado a sus horarios.",
    dependencies=[Depends(staff_required)] # <-- Permiso para staff
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


# === NUEVO ENDPOINT PARA LISTAR ALUMNOS ===
@router.get(
    "/",
    response_model=List[AlumnoListado],
    summary="Listar todos los alumnos (Admin)",
    response_description="Una lista con los detalles de cada alumno en el sistema.",
    dependencies=[Depends(staff_required)] # <-- ¡Solo para administradores!
)
async def obtener_lista_alumnos(
    db: Connection = Depends(get_db)
):
    """
    Obtiene una lista completa de todos los alumnos registrados en el sistema
    con detalles clave como su estado de actividad, cuotas pendientes y turno.

    **Este endpoint solo es accesible para usuarios con rol de administrador.**
    """
    return await listar_alumnos_detalle(conn=db)

# === NUEVO ENDPOINT PARA DETALLE DE ALUMNO ===
@router.get(
    "/{dni}",
    response_model=AlumnoDetalle,
    summary="Obtener detalles de un alumno (Staff)",
    response_description="Información detallada del alumno seleccionado.",
    dependencies=[Depends(staff_required)] # <-- ¡Solo para administradores o empleados!
)
async def obtener_alumno_por_dni(
    dni: str,
    db: Connection = Depends(get_db)
):
    """
    Obtiene una vista detallada con toda la información de un alumno específico,
    identificado por su DNI.

    **Este endpoint es accesible para usuarios con rol de staff (admin o empleado).**
    """
    return await obtener_detalle_alumno(conn=db, dni=dni)

# === NUEVO ENDPOINT PARA HORARIOS DE ALUMNO ===
@router.get(
    "/{dni}/horarios",
    response_model=HorariosAlumnoResponse,
    summary="Obtener horarios de un alumno (Staff)",
    response_description="Lista de días y grupos a los que asiste el alumno.",
    dependencies=[Depends(staff_required)] # <-- Protegido para staff
)
async def obtener_horarios_de_alumno(
    dni: str,
    db: Connection = Depends(get_db)
):
    """
    Obtiene la lista de horarios (día y grupo) asignados a un alumno específico,
    identificado por su DNI, envuelta en un objeto JSON.

    **Este endpoint es accesible para usuarios con rol de staff (admin o empleado).**
    """
    lista_horarios = await obtener_horarios_alumno(conn=db, dni=dni)
    # Devolvemos un diccionario que coincide con el esquema HorariosAlumnoResponse
    return {"horarios": lista_horarios}


@router.put(
    "/{dni}/horarios",
    response_model=HorariosAlumnoResponse,
    summary="Actualizar/Reemplazar horarios de un alumno (Staff)",
    response_description="Devuelve la nueva lista de horarios asignada al alumno.",
    dependencies=[Depends(staff_required)] # <--- Protegido para Staff
)
async def actualizar_horarios_de_alumno(
    dni: str,
    data: HorariosUpdate = Body(...), # <--- Usamos el nuevo esquema para el body
    db: Connection = Depends(get_db)
):
    """
    Reemplaza por completo la lista de horarios de un alumno activo.

    - Se eliminarán todos los horarios anteriores.
    - Se asignarán los nuevos horarios de la lista.
    - Si la lista enviada está vacía, el alumno quedará sin horarios.
    - Falla si el alumno está inactivo o si algún grupo no tiene capacidad.

    **Este endpoint es accesible para usuarios con rol de staff (admin o empleado).**
    """
    return await actualizar_horarios_alumno(conn=db, dni=dni, data=data)

@router.put(
    "/{dni}",
    response_model=AlumnoDetalle,
    summary="Actualizar perfil de un alumno (Staff)",
    response_description="Devuelve el perfil actualizado del alumno.",
    dependencies=[Depends(staff_required)] # <--- Protegido para Staff
)
async def actualizar_perfil_de_alumno(
    dni: str,
    data: AlumnoPerfilUpdate = Body(...),
    db: Connection = Depends(get_db)
):
    """
    Actualiza la información personal (nombre, apellido, email, etc.)
    y de dirección (calle, provincia, etc.) de un alumno específico.
    
    Requiere permisos de **staff (administrador o empleado)**.
    """
    return await actualizar_perfil_alumno(conn=db, dni=dni, data=data)

@router.patch(
    "/{dni}/plan",
    response_model=AlumnoDetalle,
    summary="Actualizar plan (suscripción, trabajo, nivel) de un alumno (Staff)",
    response_description="Devuelve el perfil actualizado del alumno con su nuevo plan.",
    dependencies=[Depends(staff_required)] # <--- Protegido para Staff
)
async def actualizar_plan_de_alumno(
    dni: str,
    data: AlumnoPlanUpdate = Body(...), # <--- Usamos el nuevo schema
    db: Connection = Depends(get_db)
):
    """
    Actualiza la información del plan de entrenamiento de un alumno:
    - **nombreSuscripcion**: La nueva suscripción (Debe existir).
    - **nombreTrabajo**: El nuevo tipo de trabajo (Debe existir).
    - **nivel**: El nuevo nivel (ej: "A1", "B2").

    Requiere permisos de **staff (administrador o empleado)**.
    """
    return await actualizar_plan_alumno(conn=db, dni=dni, data=data)

@router.delete(
    "/{dni}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un alumno (Staff)",
    description="Elimina permanentemente al alumno y todos sus datos asociados (Persona, Cuotas, Asistencias, etc).",
    dependencies=[Depends(staff_required)] # <-- Permite Admin y Empleado
)
async def eliminar_alumno_por_dni(
    dni: str,
    db: Connection = Depends(get_db)
):
    """
    Endpoint para dar de baja definitiva a un alumno.
    Borra al usuario de la tabla Persona y, por cascada, todo su historial.
    """
    await eliminar_alumno(conn=db, dni=dni)
    return

