from fastapi import APIRouter, Depends, Query, status # Añadir status si no está
from asyncpg import Connection
from typing import List

from core.session import get_db
from api.dependencies.security import admin_required, staff_required
from api.dependencies.auth import get_current_user

# --- Importaciones para Estadísticas ---
from schemas.estadisticasSchema import (
    DashboardKPIs,
    EntrenadorStats,
    EstadisticaTrabajoItem,
    GraficoTurnosResponse,
    EstadisticasResponse
)
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
    dependencies=[Depends(staff_required)] # <-- ¡Protegido para Administradores!
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
    dependencies=[Depends(staff_required)] 
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
    dependencies=[Depends(staff_required)]
)
async def get_stats_alumnos_turno(
    db: Connection = Depends(get_db)
):
    """
    Retorna la cantidad de alumnos activos por turno (Mañana/Tarde)
    en los últimos 7 meses.
    """
    return await estadisticasService.obtener_alumnos_por_turno_mensual(db)


@router.get(
    "/perfil-entrenador",
    response_model=EntrenadorStats,
    summary="Estadísticas personales del Entrenador",
    description="Devuelve métricas de rendimiento basadas en los grupos a cargo del usuario logueado."
)
async def get_stats_entrenador(
    current_user: dict = Depends(get_current_user), # Necesitamos saber quién es
    db: Connection = Depends(get_db)
):
    """
    Obtiene la tarjeta de rendimiento del usuario actual.
    """
    dni_empleado = current_user['dni']
    return await estadisticasService.obtener_estadisticas_entrenador(db, dni_empleado)

@router.get(
    "/rendimiento-staff",
    response_model=List[EntrenadorStats],
    summary="Rendimiento de todo el Staff (Admin)",
    description="Devuelve una lista con las métricas de cada empleado.",
    dependencies=[Depends(staff_required)]
)
async def get_all_staff_stats(
    db: Connection = Depends(get_db)
):
    return await estadisticasService.obtener_stats_todos_empleados(db)


@router.get(
    "/recaudacion",
    response_model=EstadisticasResponse,
    summary="Obtener estadísticas de recaudación mensual",
    dependencies=[Depends(staff_required)] # Solo administradores/empleados
)
async def get_recaudacion(
    mes: int = Query(..., description="Mes a consultar (1-12)"),
    anio: int = Query(..., description="Año a consultar (ej. 2026)"),
    db: Connection = Depends(get_db)
):
    """
    Obtiene el total recaudado en un mes y año específico, 
    desglosado por el administrador y los empleados, 
    discriminando los métodos de pago.
    """
    return await estadisticasService.obtener_recaudacion_mensual(conn=db, mes=mes, anio=anio)