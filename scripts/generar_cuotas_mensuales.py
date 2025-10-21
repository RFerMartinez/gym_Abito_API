
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import date, timedelta
import calendar

# Cargar variables de entorno desde el .env en la raíz
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

async def generar_cuotas():
    print(f"--- Iniciando tarea de generación de cuotas - {date.today()} ---")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL no encontrado en .env")
        return
    
    conn = None
    try:
        conn = await asyncpg.connect(database_url)
        
        # 1. Obtener todos los alumnos activos
        alumnos_activos = await conn.fetch('SELECT dni FROM "AlumnoActivo"')
        
        if not alumnos_activos:
            print("ℹ️ No hay alumnos activos para procesar.")
            return

        print(f"✅ Encontrados {len(alumnos_activos)} alumnos activos.")
        
        hoy = date.today()
        cuotas_generadas = 0

        for alumno in alumnos_activos:
            dni_alumno = alumno['dni']
            
            # 2. Obtener la última cuota generada para el alumno
            ultima_cuota = await conn.fetchrow('''
                SELECT "fechaFin" FROM "Cuota"
                WHERE dni = $1
                ORDER BY "fechaFin" DESC
                LIMIT 1
            ''', dni_alumno)
            
            # Si no tiene cuota, algo es anómalo, lo saltamos (la primera se crea al activar)
            if not ultima_cuota:
                print(f"⚠️  Alumno {dni_alumno} está activo pero no tiene cuotas. Omitiendo.")
                continue

            # 3. Comprobar si la última cuota ya venció
            if ultima_cuota['fechaFin'] < hoy:
                print(f"   -> Generando nueva cuota para el alumno {dni_alumno}...")
                
                # Obtener datos actuales del alumno para la nueva cuota
                datos_alumno = await conn.fetchrow('''
                    SELECT a."nombreSuscripcion", a."nombreTrabajo", s.precio
                    FROM "Alumno" a
                    JOIN "Suscripcion" s ON a."nombreSuscripcion" = s."nombreSuscripcion"
                    WHERE a.dni = $1
                ''', dni_alumno)

                if not datos_alumno:
                    print(f"❌ No se encontraron datos de suscripción para el alumno {dni_alumno}. Omitiendo.")
                    continue

                # 4. Crear la nueva cuota
                nueva_fecha_inicio = ultima_cuota['fechaFin'] + timedelta(days=1)
                nueva_fecha_fin = nueva_fecha_inicio + timedelta(days=30)
                nombre_mes = calendar.month_name[nueva_fecha_inicio.month].capitalize()

                await conn.execute('''
                    INSERT INTO "Cuota" (dni, pagada, monto, "fechaComienzo", "fechaFin", mes, "nombreTrabajo", "nombreSuscripcion")
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ''', dni_alumno, False, datos_alumno['precio'], nueva_fecha_inicio, nueva_fecha_fin, nombre_mes, datos_alumno['nombreTrabajo'], datos_alumno['nombreSuscripcion'])
                
                cuotas_generadas += 1

        print(f"🎉 Proceso finalizado. Se generaron {cuotas_generadas} nuevas cuotas.")

    except Exception as e:
        print(f"❌ Error durante la generación de cuotas: {e}")
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(generar_cuotas())