from datetime import datetime, timezone, timedelta
from asyncpg import Connection
from typing import Optional

import uuid

# ==============================
# Funciones para authServices.py
# ==============================
async def get_user_by_email(conn: Connection, email: str) -> Optional[dict]:
    result = await conn.fetchrow('SELECT * FROM "Persona" WHERE email = $1', email)
    return dict(result) if result else None

async def get_user_by_username(conn: Connection, username: str) -> Optional[dict]:
    result = await conn.fetchrow('SELECT * FROM "Persona" WHERE usuario = $1', username)
    return dict(result) if result else None

async def get_user_by_dni(conn: Connection, dni: str) -> Optional[dict]:
    result = await conn.fetchrow('SELECT * FROM "Persona" WHERE dni = $1', dni)
    return dict(result) if result else None

async def create_email_verification_token(conn: Connection, email: str, token: str) -> None:
    """Crea o actualiza un token de verificación de email"""
    # Eliminar tokens existentes para este email
    await conn.execute('DELETE FROM "EmailVerificationToken" WHERE email = $1', email)

    # Crear nuevo token
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    token_id = str(uuid.uuid4())

    await conn.execute('''
        INSERT INTO "EmailVerificationToken" (id, email, token, expires_at)
        VALUES ($1, $2, $3, $4)
    ''', token_id, email, token, expires_at)

async def get_email_verification_token(conn: Connection, token: str) -> Optional[dict]:
    """Obtiene un token de verificación de email"""
    result = await conn.fetchrow(
        'SELECT * FROM "EmailVerificationToken" WHERE token = $1',
        token
    )
    return dict(result) if result else None

async def delete_email_verification_token(conn: Connection, token: str) -> None:
    """Elimina un token de verificación de email"""
    await conn.execute('DELETE FROM "EmailVerificationToken" WHERE token = $1', token)