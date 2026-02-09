from fastapi import APIRouter, Depends, status, Request, HTTPException, Body
from fastapi.responses import RedirectResponse

from asyncpg import Connection

from core.session import get_db
from api.dependencies.security import admin_required, alumno_required
from services.pagoServices import crear_preferencia_pago, marcar_pago_manual, procesar_pago_exitoso, obtener_estado_pago_cuota
from schemas.pagoSchema import PreferenciaPagoResponse

from fastapi.responses import StreamingResponse
from services.pagoServices import generar_comprobante_pdf
from api.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"]
)

# 1. Endpoint para iniciar el pago (Para el Alumno)
@router.post(
    "/crear-preferencia/{id_cuota}",
    response_model=PreferenciaPagoResponse,
    summary="Crear preferencia de pago MP",
    dependencies=[Depends(alumno_required)] 
)
async def iniciar_pago_cuota(
    id_cuota: int,
    monto_final: float = Body(..., embed=True, description="Monto final calculado por el front"), # <--- Nuevo parámetro
    db: Connection = Depends(get_db)
):
    """
    Genera el link de pago (init_point) para una cuota específica.
    Recibe el monto final (con o sin recargos) calculado por el Frontend.
    """
    # Pasamos el monto_final al servicio
    return await crear_preferencia_pago(conn=db, id_cuota=id_cuota, monto_final=monto_final)


# 2. Endpoint para recibir notificaciones (Para Mercado Pago)
@router.post("/webhook", include_in_schema=False)
async def recibir_notificacion_mp(request: Request, db: Connection = Depends(get_db)):
    try:
        params = request.query_params
        owner = params.get("owner", "mia") # <--- Capturar quién es el dueño
        topic = params.get("topic") or params.get("type")
        payment_id = params.get("id") or params.get("data.id")

        if not payment_id:
            body = await request.json()
            topic = body.get("type")
            payment_id = body.get("data", {}).get("id")

        if topic == "payment" and payment_id:
            # Pasamos el owner al servicio
            await procesar_pago_exitoso(conn=db, payment_id=payment_id, owner=owner)
        
        return {"status": "ok"}
    except Exception:
        return {"status": "ok"}


# 3. Endpoint "Puente" para redirección post-pago
# Este endpoint recibe al usuario desde MP (vía Ngrok) y lo manda a Vue (Localhost)
@router.get("/retorno")
async def retorno_pago(request: Request):
    """
    Recibe la redirección de MercadoPago con los query params
    (collection_id, collection_status, external_reference, etc.)
    y redirige al usuario al Frontend local manteniendo esos datos.
    """
    # Capturamos todos los parámetros que envía MP
    params = request.query_params

    # Construimos la URL de tu Frontend
    # IMPORTANTE: Aquí pones la ruta de tu vista en Vue
    url_frontend = "http://localhost:8080/Usuario" 

    # Reconstruimos el query string para no perder datos
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])

    # URL Final: http://localhost:8080/Usuario?collection_id=...&status=approved...
    url_final = f"{url_frontend}?{query_string}"

    # Redirigimos al navegador del usuario
    return RedirectResponse(url=url_final)

@router.get("/{id_cuota}/estado", response_model=bool)
async def verificar_estado_cuota(
    id_cuota: int,
    db: Connection = Depends(get_db)
):
    """
    Devuelve True si la cuota ya fue pagada. 
    Usado por el Frontend para polling mientras se escanea el QR.
    """
    return await obtener_estado_pago_cuota(conn=db, id_cuota=id_cuota)

@router.get(
    "/comprobante/{id_cuota}",
    summary="Descargar comprobante de pago",
    dependencies=[Depends(get_current_user)]
)
async def descargar_comprobante(
    id_cuota: int, 
    db: Connection = Depends(get_db)
):
    pdf_buffer = await generar_comprobante_pdf(conn=db, id_cuota=id_cuota)
    
    if not pdf_buffer:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado o cuota no pagada")

    # Definimos el nombre exacto que quieres
    filename = "ComprobantePago.pdf"

    # Forzamos la descarga con el nombre elegido ignorando la ruta del endpoint
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Cache-Control": "no-cache" # Evita que el navegador cachee nombres viejos
    }
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers=headers
    )

# Endpoint para Pago Manual (Admin)
@router.put(
    "/marcar-pagada/{id_cuota}",
    summary="Marcar cuota como pagada (Admin)",
    dependencies=[Depends(admin_required)]
)
async def registrar_pago_manual(
    id_cuota: int,
    metodo_pago: str = Body(..., embed=True, description="Puede ser 'Efectivo' o 'Transferencia'"), 
    db: Connection = Depends(get_db)
):
    """
    Registra el pago manual de una cuota.
    El body debe ser un JSON: { "metodo_pago": "Efectivo" }
    """
    return await marcar_pago_manual(conn=db, id_cuota=id_cuota, metodo_pago=metodo_pago)

