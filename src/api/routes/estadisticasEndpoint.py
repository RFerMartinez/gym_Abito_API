from fastapi import APIRouter, Depends, status # Añadir status si no está
from asyncpg import Connection
from typing import List

from core.session import get_db
from api.dependencies.security import admin_required, staff_required
from api.dependencies.auth import get_current_user

# --- Importaciones para Estadísticas ---
from schemas.estadisticasSchema import EstadisticaTrabajoItem
from services import estadisticasService # Importamos el nuevo servicio

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get(
    "/estadisticas/alumnos-por-trabajo",
    response_model=List[EstadisticaTrabajoItem],
    summary="Obtener cantidad de alumnos por tipo de trabajo (Admin)",
    response_description="Lista con la cantidad de alumnos inscritos en cada trabajo.",
    dependencies=[Depends(admin_required)] # <-- ¡Protegido para Administradores!
)
async def get_estadisticas_alumnos_por_trabajo(
    db: Connection = Depends(get_db)
):
    """
    Obtiene un resumen estadístico de cuántos alumnos están inscritos
    en cada metodología de trabajo.

    **Este endpoint solo es accesible para usuarios con rol de administrador.**
    """
    return await estadisticasService.obtener_alumnos_por_trabajo(conn=db)