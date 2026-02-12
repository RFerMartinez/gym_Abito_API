import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.session import connect_to_db, close_db_connection, get_db

# Importamos la función de generación de cuotas
# Asegúrate de que la ruta sea correcta según tu estructura
from services.cuotaServices import generar_cuotas_masivas_mensuales 
from services.facturacionServices import procesar_cierre_automatico

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/var/www/gym_abito/backend/scheduler.log"),
        logging.StreamHandler()
    ]
)

async def tarea_generar_cuotas():
    """Esta función se ejecutará automáticamente."""
    logging.info("[Scheduler] Iniciando generación automática de cuotas...")
    try:
        # Usamos el generador de dependencias manualmente
        async for db in get_db():
            cantidad = await generar_cuotas_masivas_mensuales(db)
            if cantidad > 0:
                logging.info(f"[Scheduler] Se generaron {cantidad} cuotas.")
            else:
                logging.info("[Scheduler] No hubo cuotas para generar hoy.")
            break # Importante romper el loop del generador
    except Exception as e:
        logging.error(f"[Scheduler] Error generando cuotas: {e}")

async def tarea_cierre_facturacion():
    """Se ejecuta el día 1 y 15 para cerrar la facturación."""
    logging.info("[Scheduler] Iniciando cierre de facturación automático...")
    try:
        async for db in get_db(): 
            await procesar_cierre_automatico(db)
            logging.info("[Scheduler] Cierre de facturación finalizado con éxito.")
            break 
    except Exception as e:
        logging.error(f"[Scheduler] Error en cierre de facturación: {e}")

async def main():
    # 1. Iniciar conexión a DB
    await connect_to_db()
    
    # 2. Configurar Scheduler
    scheduler = AsyncIOScheduler()
    
    # Tarea: Generar Cuotas
    scheduler.add_job(
        tarea_generar_cuotas, 
        CronTrigger(day=6, hour=0, minute=0),
        id="generacion_cuotas_mensual"
    )

    # Tarea: Generar Cierre quincenal (Dias 1 y 15 a las 23:30)
    scheduler.add_job(
        tarea_cierre_facturacion,
        CronTrigger(day='1,15', hour=23, minute=30), # Días 1 y 15 a las 23:30
        id="cierre_facturacion_auto"
    )
    
    # 3. Iniciar
    scheduler.start()
    logging.info("Scheduler iniciado y esperando tareas...")
    
    # Mantener el script vivo infinitamente
    try:
        while True:
            await asyncio.sleep(1000)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Deteniendo Scheduler...")
        await close_db_connection()

if __name__ == "__main__":
    asyncio.run(main())
