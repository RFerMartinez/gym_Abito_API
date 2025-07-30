from fastapi import FastAPI

from core.config import settings, env_path

app = FastAPI(
    title=settings.PROJECT_TITLE,
    description=settings.PROJECT_DESCRIPTION,
    contact=settings.PROJECT_CONTACT,
    version="1.0.0"
)

print(f"ruta: {env_path}")

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