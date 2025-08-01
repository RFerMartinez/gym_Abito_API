# imports de libs ext
from asyncpg import create_pool, Pool, Connection

# imports modules app
from core.config import settings

# imports python
from typing import AsyncGenerator

# variable global para el pool de conexiones
_db_pool: Pool = None

# funcióon asíncrona para crear un pool de conexiones a la base de datos
async def create_db_pool() -> Pool:
    return await create_pool(
        dsn=settings.DATABASE_URL.unicode_string(),
        min_size=5,
        max_size=15,
        timeout=30,
        command_timeout=60,
        max_inactive_connection_lifetime=300,
        server_settings = {
            'search_path': 'public'
        }
    )

async def connect_to_db() -> None:
    global _db_pool
    _db_pool = await create_db_pool()

async def close_db_connection() -> None:
    if _db_pool:
        await _db_pool.close()

# función de conexion a la DB, para inyección de dependencias
async def get_db() -> AsyncGenerator[Connection, None]:
    async with _db_pool.acquire() as conn:
        try:
            yield conn
        finally:
            pass



