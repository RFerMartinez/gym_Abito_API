from datetime import date
from fastapi import APIRouter, Depends, Query
from asyncpg import Connection
from core.session import get_db
from api.dependencies.security import admin_required
from services.facturacionServices import generar_cierre_quincenal, obtener_reporte_facturacion

router = APIRouter(prefix="/facturacion", tags=["Contabilidad"])

@router.post("/generar-cierre", dependencies=[Depends(admin_required)])
async def realizar_cierre(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    db: Connection = Depends(get_db)
):
    id_fact = await generar_cierre_quincenal(db, fecha_inicio, fecha_fin)
    if not id_fact:
        return {"message": "No hay cuotas digitales pendientes en este rango."}
    return {"idFacturacion": id_fact, "message": "Cierre quincenal generado correctamente."}

@router.get("/reporte/{id_facturacion}", dependencies=[Depends(admin_required)])
async def ver_reporte(id_facturacion: int, db: Connection = Depends(get_db)):
    return await obtener_reporte_facturacion(db, id_facturacion)