import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.session import connect_to_db, close_db_connection, get_db

# Importamos la función de generación de cuotas
# Asegúrate de que la ruta sea correcta según tu estructura
from services.cuotaServices import generar_cuotas_masivas_mensuales 

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

async def main():
    # 1. Iniciar conexión a DB
    await connect_to_db()
    
    # 2. Configurar Scheduler
    scheduler = AsyncIOScheduler()
    
    # Tarea: Generar Cuotas (Día 12 a las 14:45)
    scheduler.add_job(
        tarea_generar_cuotas, 
        CronTrigger(day=12, hour=15, minute=7),
        id="generacion_cuotas_mensual"
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