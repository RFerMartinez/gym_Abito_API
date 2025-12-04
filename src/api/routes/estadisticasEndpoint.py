from fastapi import APIRouter, Depends, status # Añadir status si no está
from asyncpg import Connection
from typing import List

from core.session import get_db
from api.dependencies.security import admin_required, staff_required
from api.dependencies.auth import get_current_user

# --- Importaciones para Estadísticas ---
from schemas.estadisticasSchema import DashboardKPIs, EstadisticaTrabajoItem, GraficoTurnosResponse
from services import estadisticasService # Importamos el nuevo servicio

router = APIRouter(
    prefix="/admin",
    tags=["Estadísticas"]
)

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

@router.get(
    "/kpis",
    response_model=DashboardKPIs,
    summary="Obtener KPIs principales",
    dependencies=[Depends(admin_required)] 
)
async def get_dashboard_kpis(
    db: Connection = Depends(get_db)
):
    """
    Retorna los 4 indicadores clave:
    - Alumnos Activos
    - Cuotas Vencidas (Totales)
    - Ingreso Mensual (Recaudado mes actual)
    - % de Cobro (Eficiencia de cobro mes actual)
    """
    return await estadisticasService.obtener_kpis_generales(db)

@router.get(
    "/alumnos-turno",
    response_model=GraficoTurnosResponse,
    summary="Datos para gráfico de barras (Turnos)",
    dependencies=[Depends(admin_required)]
)
async def get_stats_alumnos_turno(
    db: Connection = Depends(get_db)
):
    """
    Retorna la cantidad de alumnos activos por turno (Mañana/Tarde)
    en los últimos 7 meses.
    """
    return await estadisticasService.obtener_alumnos_por_turno_mensual(db)