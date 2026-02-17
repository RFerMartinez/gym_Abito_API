#!/usr/bin/env python3
import sys
import os
import asyncio
import asyncpg
import getpass
from passlib.context import CryptContext

# --- 1. AJUSTE DE RUTAS DE IMPORTACIÓN ---
# Esto es necesario para poder importar 'core' cuando ejecutas el script directamente
# Agregamos el directorio actual (src) al path de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- 2. IMPORTAR SETTINGS ---
try:
    from core.config import settings
    print("Se importó Settings")
except ImportError:
    # Intento alternativo por si se ejecuta desde la raíz del proyecto
    sys.path.append(os.path.join(current_dir, '..'))

    from src.core.config import settings

# Contexto para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def crear_administrador():
    print("\n--- CREACIÓN DE USUARIO ADMINISTRADOR ---")
    print("==============================================")
    
    # Construimos la URL usando las variables de SETTINGS (Pydantic)
    # Asumimos que settings tiene estos atributos mapeados desde el .env
    try:
        db_user = settings.PSQL_USER
        db_pass = settings.PSQL_PASSWORD
        db_host = settings.PSQL_SERVER
        db_port = settings.PSQL_PORT
        db_name = settings.PSQL_DB # O settings.PSQL_DB_TEST si prefieres
        
        # Armamos la URL de conexión
        database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        print(f"Conectando a: {db_host}:{db_port}/{db_name}")

        print(database_url)
        
    except AttributeError as e:
        print(f"Error en configuración: Falta alguna variable en settings. {e}")
        return

    # --- SOLICITUD DE DATOS AL USUARIO ---
    print("\nIngrese los datos del nuevo Administrador:\n")
    
    dni = input("DNI: ").strip()
    nombre = input("Nombre: ").strip()
    apellido = input("Apellido: ").strip()
    telefono = input("Teléfono: ").strip()
    email = input("Email: ").strip()
    usuario_login = input("Usuario para Login (ej: admin): ").strip()

    # Validación de contraseña doble
    password_final = ""
    while True:
        p1 = getpass.getpass("Contraseña: ")
        p2 = getpass.getpass("Repita la Contraseña: ")
        
        if not p1:
            print("La contraseña no puede estar vacía.")
            continue
            
        if p1 == p2:
            password_final = p1
            break
        else:
            print("Las contraseñas no coinciden. Intente nuevamente.\n")

    conn = None
    try:
        # Conexión asíncrona
        conn = await asyncpg.connect(database_url)
        
        # 1. Validar que no exista el usuario
        existe_user = await conn.fetchval('SELECT 1 FROM "Persona" WHERE usuario = $1', usuario_login)
        if existe_user:
            print(f"\nError: El usuario '{usuario_login}' ya existe.")
            return

        # 2. Validar que no exista el DNI
        existe_dni = await conn.fetchval('SELECT 1 FROM "Persona" WHERE dni = $1', dni)
        if existe_dni:
            print(f"\nError: El DNI '{dni}' ya está registrado.")
            return

        # 3. Hashear contraseña
        hashed_password = pwd_context.hash(password_final)
        
        # 4. Insertar en la base de datos
        # IMPORTANTE: Asumo que la tabla es "Persona". Ajusta los campos si tu modelo es diferente.
        await conn.execute('''
            INSERT INTO "Persona" 
            (dni, nombre, apellido, telefono, email, usuario, contrasenia, "requiereCambioClave", "esAdmin")
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ''', 
        dni, nombre, apellido, telefono, email, usuario_login, 
        hashed_password, False, True)

        print("\n¡Administrador creado exitosamente!")
        print(f"   Usuario: {usuario_login}")
        print("   Puede iniciar sesión inmediatamente.")
        print("==============================================\n")

    except Exception as e:
        print(f"\nOcurrió un error inesperado: {e}")
    finally:
        if conn:
            await conn.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    try:
        asyncio.run(crear_administrador())
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")