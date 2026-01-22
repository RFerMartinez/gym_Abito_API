
from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import Connection
from typing import List

# --- Dependencias y Sesión ---
from core.session import get_db
from api.dependencies.security import alumno_required, staff_required

# --- Schemas y Services ---
from schemas.cuotaSchema import (
    CuotaResponseAlumnoAuth,
    CuotaResponsePorDNI,
    CuotaUpdateRequest
)
from services.cuotaServices import (
    obtener_cuotas_por_dni,
    obtener_cuotas_por_alumno,
    modificar_cuota,
    eliminar_cuota
)

router = APIRouter(
    prefix="/cuotas",
    tags=["Cuotas"]
)

@router.get(
    "/mis-cuotas",
    response_model=List[CuotaResponseAlumnoAuth],
    summary="Listar mis cuotas (alumno autenticado)",
    dependencies=[Depends(alumno_required)] # <-- Protegido para alumnos
)
async def listar_mis_cuotas(
    current_user: dict = Depends(alumno_required),
    db: Connection = Depends(get_db)
):
    """
    Obtiene el historial de cuotas (pagadas y pendientes)
    del alumno actualmente autenticado.
    """
    dni_alumno = current_user['dni']
    return await obtener_cuotas_por_alumno(db, dni_alumno)

@router.get(
    "/alumno/{dni}",
    response_model=List[CuotaResponsePorDNI],
    summary="Obtener cuotas de un alumno específico (Staff)",
    dependencies=[Depends(staff_required)] # ¡AQUÍ PROTEGEMOS LA RUTA!
)
async def listar_cuotas_de_alumno(
    dni: str,
    db: Connection = Depends(get_db)
):
    """
    Endpoint para que un administrador o empleado pueda ver todas las
    cuotas de un alumno específico, identificado por su DNI.
    
    Requiere permisos de **staff (administrador o empleado)**.
    """
    return await obtener_cuotas_por_dni(conn=db, dni=dni)

@router.put(
    "/{id_cuota}",
    summary="Modificar una cuota (Staff)",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(staff_required)] # Solo administradores/empleados
)
async def actualizar_cuota(
    id_cuota: int,
    cuota_data: CuotaUpdateRequest,
    db: Connection = Depends(get_db)
):
    """
    Actualiza una cuota existente.
    - Si se marca como NO PAGADA, se borran fecha, hora y método de pago.
    """
    # Validación extra de seguridad (opcional): asegurar que el ID de la URL coincida con el del body
    if id_cuota != cuota_data.idCuota:
        raise HTTPException(status_code=400, detail="El ID de la URL no coincide con el ID del cuerpo de la petición")

    updated = await modificar_cuota(conn=db, id_cuota=id_cuota, cuota_data=cuota_data)
    
    return {"message": "Cuota actualizada correctamente", "success": updated}


@router.delete(
    "/{id_cuota}",
    summary="Eliminar una cuota (Staff)",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(staff_required)] # Solo staff puede borrar
)
async def borrar_cuota(
    id_cuota: int,
    db: Connection = Depends(get_db)
):
    """
    Elimina permanentemente una cuota del sistema.
    """
    await eliminar_cuota(conn=db, id_cuota=id_cuota)
    return {"message": "Cuota eliminada correctamente", "success": True}

