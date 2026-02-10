# imports FastAPI
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Cron Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Imports Dependencies
from api.dependencies.auth import get_current_user

# imports UTILs
from contextlib import asynccontextmanager

# imports EXCEPTIONS
from utils.exceptions import AppException

# imports settings, session
from core.config import settings, env_path
from core.session import connect_to_db, close_db_connection, get_db

# imports endPoints
from api.routes.suscripcionEndpoint import router as suscripcion_endpoint       # suscripcion
from api.routes.trabajoEndpoint import router as trabajo_endpoint               # trabajo
from api.routes.horarioEndpoint import router as horario_endpoint               # horarios (grupo y dia)
from api.routes.ubicacionEndpoint import router as ubicacion_endpoint           # ubicacion (direccion)
from api.routes.authEndpoint import router as auth_endpoint                     # auth (login, register)
from api.routes.alumnosEndpoint import router as alumnos_endpoint               # alumnos (acttivar alumno)
from api.routes.reclamoEndpoint import router as reclamo_endpoint               # reclamos
from api.routes.cuotaEndpoint import router as cuota_endpoint                   # cuotas
from api.routes.personaEndpoint import router as persona_endpoint               # personas
from api.routes.estadisticasEndpoint import router as estadisticas_endpoint     # EndPoint
from api.routes.avisoEndpoint import router as aviso_endpoint                   # avisos
from api.routes.empleadoEndpoint import router as empleado_endpoint             # empleados
from api.routes.pagosEndpoint import router as pagos_endpoint                   # MercadoPago
from api.routes.facturacionEndpoint import router as facturacion_endpoint       # Facturacion

from api.routes.adminExample import router as admin_example_endpoint            # ejemplo admin
from api.routes.alumnosExample import router as alumnos_example_endpoint        # ejemplo alumnos

from services.cuotaServices import generar_cuotas_masivas_mensuales
from services.facturacionServices import procesar_cierre_automatico


# FUNCIONES WRAPPER -----------
async def tarea_generar_cuotas():
    """Esta función se ejecutará automáticamente el día 5."""
    print("[Scheduler] Iniciando generación automática de cuotas...")
    async for db in get_db(): # Obtenemos conexión del pool
        cantidad = await generar_cuotas_masivas_mensuales(db)
        if cantidad > 0:
            print(f"[Scheduler] Se generaron {cantidad} cuotas.")
        break

async def tarea_cierre_facturacion():
    """Se ejecuta el día 1 y 15 para cerrar la facturación."""
    print("[Scheduler] Iniciando cierre de facturación automático...")
    # Usamos el generador de dependencias tal como en tarea_generar_cuotas
    async for db in get_db(): 
        await procesar_cierre_automatico(db)
        break # Importante: romper el bucle ya que get_db es un generador
# ------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. INICIO DE LA APP
    
    # A) Conectar Base de Datos (TU CÓDIGO ACTUAL)
    await connect_to_db()
    print("Conexión a la base de datos establecida")
    print(f"url_ngrok: {settings.URL_NGROK}")

    # B) Iniciar Scheduler (LO NUEVO)
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        tarea_generar_cuotas, 
        CronTrigger(day=5, hour=0, minute=0), # Día 5 de cada mes a las 08:00 hs
        id="generacion_cuotas_mensual"
    )

    scheduler.add_job(
        tarea_cierre_facturacion,
        CronTrigger(day='1,15', hour=23, minute=30),
        id="cierre_facturacion_auto"
    )
    
    scheduler.start()
    print("Planificador de tareas (Scheduler) iniciado.")
    
    yield # <--- Aquí la app corre y recibe peticiones
    
    # 2. APAGADO DE LA APP
    
    # C) Apagar Scheduler (LO NUEVO)
    print("Deteniendo planificador...")
    scheduler.shutdown()
    
    # D) Desconectar Base de Datos (TU CÓDIGO ACTUAL)
    await close_db_connection()
    print("Conexión a la base de datos cerrada")

app = FastAPI(
    title=settings.PROJECT_TITLE,
    description=settings.PROJECT_DESCRIPTION,
    contact=settings.PROJECT_CONTACT,
    version="1.0.0",
    lifespan=lifespan
)

# Configuración CORS
# Orífgenes permitidos
origins = [
    "http://localhost:8081",
    "http://localhost:8080",
    "https://gymabito.com",
    "https://www.gymabito.com"
]
# Agregar el middleware CORS a la aplicación
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],  # Métodos permitidos
    allow_headers=["*"],  # Encabezados permitidos
)

# Handler global para excepciones personalizadas
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "type": exc.__class__.__name__,
            "status": exc.status_code
        }
    )

# Handler para excepciones generales (opcional pero recomendado)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # En producción, podrías querer loguear el error real pero no exponerlo
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "type": "InternalServerError",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
    )

# Anexando los distintos endpoints
app.include_router(auth_endpoint)
app.include_router(admin_example_endpoint)
app.include_router(alumnos_example_endpoint)
app.include_router(suscripcion_endpoint)
app.include_router(trabajo_endpoint)
app.include_router(horario_endpoint)
app.include_router(ubicacion_endpoint)
app.include_router(alumnos_endpoint)
app.include_router(reclamo_endpoint)
app.include_router(cuota_endpoint)
app.include_router(persona_endpoint)
app.include_router(estadisticas_endpoint)
app.include_router(aviso_endpoint)
app.include_router(empleado_endpoint)
app.include_router(pagos_endpoint)
app.include_router(facturacion_endpoint)

if __name__ == "__main__":
    import uvicorn
    
    # Esto solo se ejecuta si ejecutas este archivo directamente (python main.py)
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        # log_level="info"
    )

print(f"database_url: {settings.DATABASE_URL}")
