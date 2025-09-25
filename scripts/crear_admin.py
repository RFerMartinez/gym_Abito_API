#!/usr/bin/env python3
"""
Script simple para crear usuario administrador
"""

import asyncio
import asyncpg
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el .env en la raíz
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def crear_administrador():
    print("👨‍💼 Creando Usuario Administrador")
    print("================================")
    
    # Obtener datos de conexión directamente de .env
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL no encontrado en .env")
        return
    
    admin_data = {
        "dni": "00000000",
        "nombre": "Admin",
        "apellido": "Sistema", 
        "telefono": "0000000000",
        "email": "admin@gimnasio.com",
        "usuario": "admin",
        "password": "admin123",
        "esAdmin": True
    }
    
    try:
        # Conectar a la base de datos
        conn = await asyncpg.connect(database_url)
        
        # Verificar si ya existe
        existe = await conn.fetchval(
            'SELECT 1 FROM "Persona" WHERE usuario = $1', 
            admin_data["usuario"]
        )
        
        if existe:
            print("ℹ️  El administrador ya existe")
            await conn.close()
            return
        
        # Hashear contraseña
        hashed_password = pwd_context.hash(admin_data["password"])
        
        # Crear administrador
        await conn.execute('''
            INSERT INTO "Persona" 
            (dni, nombre, apellido, telefono, email, usuario, contrasenia, "requiereCambioClave", "esAdmin")
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ''', 
        admin_data["dni"], admin_data["nombre"], admin_data["apellido"], 
        admin_data["telefono"], admin_data["email"], admin_data["usuario"],
        hashed_password, True, admin_data["esAdmin"])
        
        print("✅ Administrador creado exitosamente!")
        print(f"📋 Usuario: {admin_data['usuario']}")
        print(f"🔑 Contraseña: {admin_data['password']}")
        print("⚠️  Debe cambiar la contraseña en el primer login")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(crear_administrador())