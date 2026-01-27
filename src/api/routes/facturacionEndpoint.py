from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import Connection
from typing import List
from datetime import date

from core.session import get_db
from schemas.facturacionSchema import FacturacionResponse, ReporteFacturacion
from services import facturacionServices
from api.dependencies.security import admin_required

router = APIRouter(
    prefix="/facturacion",
    tags=["Facturacion"]
)

@router.post(
    "/generar-cierre",
    dependencies=[Depends(admin_required)],
    response_model=List[FacturacionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generar cierre de facturación quincenal"
)
async def generar_cierre(
    fecha_inicio: date, 
    fecha_fin: date,
    db: Connection = Depends(get_db)
):
    try:
        resultado = await facturacionServices.generar_cierre_quincenal(db, fecha_inicio, fecha_fin)
        if not resultado:
            return [] # Retorna lista vacía si no hubo nada que facturar
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar cierre: {str(e)}")

@router.get(
    "/reporte/{id_facturacion}",
    dependencies=[Depends(admin_required)],
    response_model=ReporteFacturacion,
    summary="Obtener reporte detallado de una facturación"
)
async def obtener_reporte(
    id_facturacion: int,
    db: Connection = Depends(get_db)
):
    try:
        reporte = await facturacionServices.obtener_reporte_por_id(db, id_facturacion)
        if not reporte:
            raise HTTPException(status_code=404, detail="Facturación no encontrada")
        return reporte
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener reporte: {str(e)}")

