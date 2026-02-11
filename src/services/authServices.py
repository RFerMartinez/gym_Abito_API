from datetime import datetime, timezone
from asyncpg import Connection
from typing import Optional

from schemas.authSchema import (
    PasswordResetConfirm,
    RegistroPaso1,
    RegistroPaso2
)

from utils.exceptions import (
    BusinessRuleException,
    DuplicateEntryException,
    DatabaseException,
    NotFoundException
)

from utils.email import email_service

from utils.security import (
    verify_password,
    get_password_hash,
    generate_verification_token,
    create_registration_token,
    verify_registration_token,
    create_password_reset_token,
    verify_password_reset_token,
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

# MODIFICAMOS ESTA FUNCIÓN
async def iniciar_registro_paso1(conn: Connection, user_data: RegistroPaso1) -> str:
    """Inicia el proceso de registro (Paso 1) y devuelve un JWT."""
    # Verificar si el email ya existe
    if await get_user_by_email(conn, user_data.email):
        raise DuplicateEntryException("Email", user_data.email)

    # Verificar si el usuario ya existe
    if await get_user_by_username(conn, user_data.usuario):
        raise DuplicateEntryException("Usuario", user_data.usuario)

    # Crear el token JWT con los datos del Paso 1
    registration_data = {
        "email": user_data.email,
        "usuario": user_data.usuario,
        "contrasenia": user_data.contrasenia # Guardamos la contraseña en texto plano en el token temporal
    }
    token = create_registration_token(data=registration_data)

    # Enviar email de verificación (solo si el servicio está configurado)
    if email_service is None:
        print("Servicio de email no configurado, omitiendo envío")
    else:
        print(f"Intentando enviar email a: {user_data.email}")
        # El token que enviamos en el email ahora es el JWT
        # NOTA: En producción, es mejor enviar un token opaco y no el JWT directamente en la URL
        # pero para este ejemplo, es funcional.
        success = await email_service.send_verification_email(user_data.email, token)

        if not success:
            print("No se pudo enviar el email de verificación, pero el registro continuará")

    return token

async def completar_registro_paso2(conn: Connection, user_data: RegistroPaso2, email: str, usuario: str, contrasenia: str) -> dict:
    """Completa el proceso de registro (Paso 2)"""
    # Verificar si el DNI ya existe
    if await get_user_by_dni(conn, user_data.dni):
        raise DuplicateEntryException("DNI", user_data.dni)

    # Hashear la contraseña
    hashed_password = get_password_hash(contrasenia)

    # Insertar la Persona con todos sus datos, incluyendo sexo
    result = await conn.fetchrow('''
        INSERT INTO "Persona" (dni, nombre, apellido, telefono, email, usuario, contrasenia, "requiereCambioClave", sexo)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
    ''', 
    user_data.dni, 
    user_data.nombre, 
    user_data.apellido, 
    user_data.telefono,
    email, 
    usuario, 
    hashed_password, 
    False, 
    user_data.sexo
    )

    user = dict(result)

    # --- CORRECCIÓN: Asegurar existencia de Provincia y Localidad ---
    
    # 1. Crear Provincia si no existe
    await conn.execute('''
        INSERT INTO "Provincia" ("nomProvincia")
        VALUES ($1)
        ON CONFLICT ("nomProvincia") DO NOTHING
    ''', user_data.nomProvincia)
    
    # 2. Crear Localidad si no existe
    await conn.execute('''
        INSERT INTO "Localidad" ("nomLocalidad", "nomProvincia")
        VALUES ($1, $2)
        ON CONFLICT ("nomLocalidad", "nomProvincia") DO NOTHING
    ''', user_data.nomLocalidad, user_data.nomProvincia)

    # Crear la dirección
    try:
        await conn.execute('''
            INSERT INTO "Direccion" ("nomLocalidad", "nomProvincia", numero, calle, dni)
            VALUES ($1, $2, $3, $4, $5)
        ''', user_data.nomLocalidad, user_data.nomProvincia, user_data.numero,
            user_data.calle, user_data.dni)
    except Exception as e:
        # Si falla la dirección, hacemos rollback manual de la persona para no dejar datos huérfanos
        await conn.execute('DELETE FROM "Persona" WHERE dni = $1', user_data.dni)
        raise DatabaseException("crear dirección", str(e))

    if email_service is not None:
        await email_service.send_welcome_email(email, user_data.nombre)

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
# ====================================


async def obtener_tipo_usuario(conn: Connection, dni: str) -> dict:
    """Obtiene el tipo de usuario y sus permisos"""
    return {
        "esAdmin": await es_administrador(conn, dni),
        "esEmpleado": await es_empleado(conn, dni),
        "esAlumnoActivo": await es_alumno_activo(conn, dni),
        "esAlumnoInactivo": await es_alumno_inactivo(conn, dni),
        "esAlumno": await es_alumno(conn, dni)
    }

async def solicitar_recuperacion_contrasenia(conn: Connection, email: str) -> None:
    """
    1. Verifica si el email existe.
    2. Genera un token de recuperación.
    3. Envía el email.
    """
    # 1. Verificar existencia
    usuario = await get_user_by_email(conn, email)
    if not usuario:
        # Lanza error para avisar al frontend (o podrías retornar OK por seguridad silenciosa)
        raise NotFoundException("Usuario con email", email)

    # 2. Generar Token (Reutilizamos la lógica de JWT con propósito específico)
    # Usamos 'create_registration_token' porque crea tokens de corta duración (15 min)
    token_data = {
        "sub": usuario['usuario'], # Guardamos el usuario o DNI
        "email": email,
    }
    token = create_password_reset_token(token_data)

    # 3. Enviar Email
    if email_service:
        await email_service.send_password_reset_email(email, token)
    else:
        print(f"Simulando envío de email a {email} con token: {token}")

async def ejecutar_recuperacion_contrasenia(conn: Connection, data: PasswordResetConfirm) -> None:
    """
    1. Valida el token.
    2. Hashea la nueva contraseña.
    3. Actualiza la base de datos.
    """
    # 1. Validar Token
    payload = verify_password_reset_token(data.token) # Reutiliza la función de verificación
    
    if not payload or payload.get("purpose") != "password_reset":
        raise BusinessRuleException("El enlace de recuperación es inválido o ha expirado.")

    email_token = payload.get("email")
    
    # 2. Actualizar contraseña
    hashed_password = get_password_hash(data.new_password)
    
    result = await conn.execute(
        'UPDATE "Persona" SET contrasenia = $1 WHERE email = $2',
        hashed_password, email_token
    )

    if result == "UPDATE 0":
        raise NotFoundException("Usuario", email_token)

async def cambiar_contrasenia_primer_ingreso(conn: Connection, dni: str, new_password: str) -> None:
    """
    Actualiza la contraseña del usuario logueado y desactiva el flag 'requiereCambioClave'.
    """
    # 1. Hashear la nueva contraseña
    hashed_password = get_password_hash(new_password)
    
    # 2. Actualizar en BD
    await conn.execute(
        'UPDATE "Persona" SET contrasenia = $1, "requiereCambioClave" = FALSE WHERE dni = $2',
        hashed_password, dni
    )

