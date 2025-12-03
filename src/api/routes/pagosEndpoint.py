from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.responses import RedirectResponse  # <--- NUEVO IMPORT

from asyncpg import Connection

from core.session import get_db
from api.dependencies.security import alumno_required
from services.pagoServices import crear_preferencia_pago, procesar_pago_exitoso
from schemas.pagoSchema import PreferenciaPagoResponse

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"]
)

# 1. Endpoint para iniciar el pago (Para el Alumno)
@router.post(
    "/crear-preferencia/{id_cuota}",
    response_model=PreferenciaPagoResponse,
    summary="Crear preferencia de pago MP",
    dependencies=[Depends(alumno_required)] # <-- Solo alumnos autenticados
)
async def iniciar_pago_cuota(
    id_cuota: int,
    db: Connection = Depends(get_db)
):
    """
    Genera el link de pago (init_point) para una cuota específica.
    """
    return await crear_preferencia_pago(conn=db, id_cuota=id_cuota)


# 2. Endpoint para recibir notificaciones (Para Mercado Pago)
@router.post("/webhook", include_in_schema=False) # Oculto de la doc para no confundir
async def recibir_notificacion_mp(
    request: Request,
    db: Connection = Depends(get_db)
):
    """
    Recibe las notificaciones de MercadoPago.
    MP envía un JSON con el 'type' y 'data.id'.
    """
    try:
        # Obtenemos los parámetros de la URL (MP suele enviar ?topic=payment&id=...)
        # O el body JSON. MP a veces varía, revisamos ambos.
        params = request.query_params
        topic = params.get("topic") or params.get("type")
        payment_id = params.get("id") or params.get("data.id")

        # Si viene en el body (formato más nuevo)
        if not payment_id:
            body = await request.json()
            topic = body.get("type")
            data = body.get("data", {})
            payment_id = data.get("id")

        if topic == "payment" and payment_id:
            await procesar_pago_exitoso(conn=db, payment_id=payment_id)
        
        # Siempre responder 200 OK a MercadoPago, o seguirán enviando la alerta
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Error en webhook: {e}")
        # Aunque falle, respondemos OK para que MP no reintente infinitamente
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

