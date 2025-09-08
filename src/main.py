# imports FastAPI
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

# imports UTILs
from contextlib import asynccontextmanager

# imports EXCEPTIONS
from utils.exceptions import AppException

# imports settings, session
from core.config import settings, env_path
from core.session import connect_to_db, close_db_connection

# imports endPoints
from api.routes.usersEndpoint import router as user_endpoint                    # user
from api.routes.suscripcionEndpoint import router as suscripcion_endpoint       # suscripcion
from api.routes.trabajoEndpoint import router as trabajo_endpoint               # trabajo
from api.routes.horarioEndpoint import router as horario_endpoint               # horarios (grupo y dia)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start app
    await connect_to_db()
    print("Conexión a la base de datos establecida")

    yield

    # Shutdown app
    await close_db_connection()
    print("Conexión a la base de datos cerrada")

app = FastAPI(
    title=settings.PROJECT_TITLE,
    description=settings.PROJECT_DESCRIPTION,
    contact=settings.PROJECT_CONTACT,
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(user_endpoint)
app.include_router(suscripcion_endpoint)
app.include_router(trabajo_endpoint)
app.include_router(horario_endpoint)

print(f"ruta: {env_path}")
print(f"Data base: {settings.DATABASE_URL}")
print(f"Tipo de dato de DataBase: {type(settings.DATABASE_URL)}")

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
