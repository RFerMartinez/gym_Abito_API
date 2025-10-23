
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from api.dependencies.security import alumno_required
from schemas.cuotaSchema import CuotaResponse
from services import cuotaServices

router = APIRouter(
    prefix="/cuotas",
    tags=["Cuotas"],
    dependencies=[Depends(alumno_required)] # <-- Protegido para alumnos
)

@router.get(
    "/mis-cuotas",
    response_model=List[CuotaResponse],
    summary="Listar mis cuotas (alumno autenticado)"
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
    return await cuotaServices.obtener_cuotas_por_alumno(db, dni_alumno)

