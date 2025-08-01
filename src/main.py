# imports FastAPI
from fastapi import FastAPI

# imports UTILs
from contextlib import asynccontextmanager

# imports settings, session
from core.config import settings, env_path
from core.session import connect_to_db, close_db_connection

# imports endPoints
from api.routes.usersEndpoint import router as user_endpoint
from api.routes.suscripcionEndpoint import router as suscripcion_endpoint
from api.routes.trabajoEndpoint import router as trabajo_endpoint

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

# Anexando los distintos endpoints
app.include_router(user_endpoint)
app.include_router(suscripcion_endpoint)
app.include_router(trabajo_endpoint)

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
