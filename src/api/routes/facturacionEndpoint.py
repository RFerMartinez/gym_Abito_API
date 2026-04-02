from fastapi import APIRouter, Depends, HTTPException, Response, status
from asyncpg import Connection
from typing import List
from datetime import date

from core.session import get_db
from schemas.facturacionSchema import FacturacionResponse, ReporteFacturacion
from services import facturacionServices
from api.dependencies.security import admin_required, staff_required

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

@router.get(
    "/reporte/{id_facturacion}/pdf",
    summary="Descargar/Visualizar reporte PDF",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Retorna el archivo PDF."
        }
    }
)
async def obtener_reporte_pdf(
    id_facturacion: int,
    db: Connection = Depends(get_db)
):
    try:
        # 1. Obtenemos los datos (reutilizando la lógica existente)
        reporte_data = await facturacionServices.obtener_reporte_por_id(db, id_facturacion)
        
        if not reporte_data:
            raise HTTPException(status_code=404, detail="Facturación no encontrada")

        # 2. Generamos el PDF
        pdf_bytes = facturacionServices.generar_pdf_reporte(reporte_data)

        # 3. Retornamos como respuesta streaming/raw
        headers = {
            'Content-Disposition': f'inline; filename="Reporte_Facturacion_{id_facturacion}.pdf"'
        }
        
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")


@router.get(
    "/",
    response_model=List[FacturacionResponse],
    summary="Listar historial de facturaciones (Solo Admin)",
    description="Devuelve todas las facturaciones generadas hasta la fecha."
)
async def listar_facturaciones(
    db: Connection = Depends(get_db),
    current_user: dict = Depends(staff_required) # <--- Candado de seguridad
):
    try:
        facturas = await facturacionServices.obtener_todas_facturaciones(db)
        return facturas
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error al obtener el historial: {str(e)}"
        )

