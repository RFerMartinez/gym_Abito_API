from datetime import datetime, timezone
from asyncpg import Connection
from typing import Optional

from schemas.authSchema import RegistroPaso1, RegistroPaso2
from utils.exceptions import DuplicateEntryException, DatabaseException
from utils.email import email_service
from utils.security import (
    verify_password,
    get_password_hash,
    generate_verification_token
)
from utils.simpleQueries import (
    get_user_by_email,
    get_user_by_username,
    get_user_by_dni,
    create_email_verification_token,
    get_email_verification_token,
    delete_email_verification_token
)

import re

async def iniciar_registro_paso1(conn: Connection, user_data: RegistroPaso1) -> str:
    """Inicia el proceso de registro (Paso 1)"""
    # Verificar si el email ya existe
    if await get_user_by_email(conn, user_data.email):
        raise DuplicateEntryException("Email", user_data.email)

    # Verificar si el usuario ya existe
    if await get_user_by_username(conn, user_data.usuario):
        raise DuplicateEntryException("Usuario", user_data.usuario)

    # Generar token de verificación
    verification_token = generate_verification_token()

    # Guardar token en base de datos
    await create_email_verification_token(conn, user_data.email, verification_token)

    # Enviar email de verificación (solo si el servicio está configurado)
    if email_service is None:
        print("⚠️  Servicio de email no configurado, omitiendo envío")
    else:
        print(f"📧 Intentando enviar email a: {user_data.email}")
        success = await email_service.send_verification_email(user_data.email, verification_token)

        if not success:
            print("⚠️  No se pudo enviar el email de verificación, pero el registro continuará")

    return verification_token

async def completar_registro_paso2(conn: Connection, user_data: RegistroPaso2, email: str, usuario: str, contrasenia: str) -> dict:
    """Completa el proceso de registro (Paso 2)"""
    # Verificar si el DNI ya existe
    if await get_user_by_dni(conn, user_data.dni):
        raise DuplicateEntryException("DNI", user_data.dni)

    # Hashear la contraseña
    hashed_password = get_password_hash(contrasenia)

    # Crear la persona
    result = await conn.fetchrow('''
        INSERT INTO "Persona" (dni, nombre, apellido, telefono, email, usuario, contrasenia, "requiereCambioClave")
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
    ''', user_data.dni, user_data.nombre, user_data.apellido, user_data.telefono,
        email, usuario, hashed_password, False)

    user = dict(result)

    # Crear la dirección
    try:
        await conn.execute('''
            INSERT INTO "Direccion" ("nomLocalidad", "nomProvincia", numero, calle, dni)
            VALUES ($1, $2, $3, $4, $5)
        ''', user_data.nomLocalidad, user_data.nomProvincia, user_data.numero,
            user_data.calle, user_data.dni)
    except Exception as e:
        # Si hay error con la dirección, hacemos rollback del usuario
        await conn.execute('DELETE FROM "Persona" WHERE dni = $1', user_data.dni)
        raise DatabaseException("crear dirección", str(e))

    # Enviar email de bienvenida
    if email_service is not None:
        email_service.send_welcome_email(email, user_data.nombre)

    return user

async def authenticate_user(conn: Connection, username: str, password: str) -> Optional[dict]:
    """Autentica un usuario por username/email y contraseña"""
    # Determinar si es email o username
    if re.match(r"[^@]+@[^@]+\.[^@]+", username):
        user = await get_user_by_email(conn, username)
    else:
        user = await get_user_by_username(conn, username)

    if not user:
        return None

    if not verify_password(password, user["contrasenia"]):
        return None

    return user

async def verify_email_token(conn: Connection, token: str) -> Optional[str]:
    """Verifica un token de email y devuelve el email asociado"""
    verification_token = await get_email_verification_token(conn, token)

    if not verification_token:
        return None

    # Verificar si el token ha expirado
    expires_at = verification_token["expires_at"]
    if datetime.now(timezone.utc) > expires_at:
        await delete_email_verification_token(conn, token)
        return None

    email = verification_token["email"]
    await delete_email_verification_token(conn, token)
    return email

# ===================================
# Verificación usuario/admin/Empleado
# ===================================
async def es_administrador(conn: Connection, dni: str) -> bool:
    """Verifica si un usuario es administrador"""
    result = await conn.fetchval(
        'SELECT "esAdmin" FROM "Persona" WHERE dni = $1', 
        dni
    )
    return result if result else False

async def es_empleado(conn: Connection, dni: str) -> bool:
    """Verifica si un usuario es empleado"""
    result = await conn.fetchval(
        'SELECT 1 FROM "Empleado" WHERE dni = $1', 
        dni
    )
    return result is not None

async def es_alumno_activo(conn: Connection, dni: str) -> bool:
    """Verifica si un usuario es alumno activo"""
    result = await conn.fetchval(
        'SELECT 1 FROM "AlumnoActivo" WHERE dni = $1', 
        dni
    )
    return result is not None

async def es_alumno_inactivo(conn: Connection, dni: str) -> bool:
    """Verifica si un usuario es alumno inactivo"""
    result = await conn.fetchval(
        'SELECT 1 FROM "AlumnoInactivo" WHERE dni = $1', 
        dni
    )
    return result is not None

async def es_alumno(conn: Connection, dni: str) -> bool:
    """Verifica si un usuario es alumno (activo o inactivo)"""
    result = await conn.fetchval(
        'SELECT 1 FROM "Alumno" WHERE dni = $1', 
        dni
    )
    return result is not None

async def obtener_tipo_usuario(conn: Connection, dni: str) -> dict:
    """Obtiene el tipo de usuario y sus permisos"""
    return {
        "esAdmin": await es_administrador(conn, dni),
        "esEmpleado": await es_empleado(conn, dni),
        "esAlumnoActivo": await es_alumno_activo(conn, dni),
        "esAlumnoInactivo": await es_alumno_inactivo(conn, dni),
        "esAlumno": await es_alumno(conn, dni)
    }