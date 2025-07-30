from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, SecretStr

from core.constants import TITLE, APP_NAME, DESCRIPTION, CONTACT

# ruta del archivo .env
env_path = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    # -- CONFIG PARA PROYECTO
    PROJECT_TITLE: str = TITLE
    PROJECT_NAME: str = APP_NAME
    PROJECT_DESCRIPTION: str = DESCRIPTION
    PROJECT_CONTACT: dict = CONTACT

    # -- CONFIG PARA BASE DE DATO
    PSQL_SERVER: str
    PSQL_USER: str
    PSQL_PASSWORD: SecretStr
    PSQL_DB: str
    PSQL_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.PSQL_USER,
            password=self.PSQL_PASSWORD.get_secret_value(),
            host=self.PSQL_SERVER,
            port=self.PSQL_PORT,
            path=self.PSQL_DB
        )
    
    class Config:
        env_file = env_path
        case_sensitive = True

# módulo para exportar
settings = Settings()
