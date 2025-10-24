
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

# --- Dependencias y Sesión ---
from core.session import get_db
from api.dependencies.security import alumno_required, staff_required

# --- Schemas y Services ---
from schemas.cuotaSchema import CuotaResponse
from services.cuotaServices import (
    obtener_cuotas_por_dni,
    obtener_cuotas_por_alumno
)

router = APIRouter(
    prefix="/cuotas",
    tags=["Cuotas"]
)

@router.get(
    "/mis-cuotas",
    response_model=List[CuotaResponse],
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
    response_model=List[CuotaResponse],
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

