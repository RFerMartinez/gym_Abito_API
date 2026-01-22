
import calendar
from datetime import date, timedelta
from asyncpg import Connection
from typing import List

from schemas.cuotaSchema import (
    CuotaResponseAlumnoAuth,
    CuotaResponsePorDNI,
    CuotaUpdateRequest
)
from utils.exceptions import (
    DatabaseException,
    NotFoundException
)

# === DICCIONARIO PARA TRADUCCIÓN DE MESES ===
meses_es = {
    "January": "Enero",
    "February": "Febrero",
    "March": "Marzo",
    "April": "Abril",
    "May": "Mayo",
    "June": "Junio",
    "July": "Julio",
    "August": "Agosto",
    "September": "Septiembre",
    "October": "Octubre",
    "November": "Noviembre",
    "December": "Diciembre"
}

# Obtiene las cuotas de UN SOLO alumno (Auth)
async def obtener_cuotas_por_alumno(conn: Connection, dni_alumno: str) -> List[CuotaResponseAlumnoAuth]:
    """Obtiene todas las cuotas de un alumno específico, ordenadas por fecha."""
    try:
        query = """
        SELECT
            "idCuota",
            mes,
            EXTRACT(YEAR FROM "fechaFin")::INTEGER as anio,
            "nombreTrabajo" as trabajo,
            "nombreSuscripcion" as suscripcion,
            monto,
            pagada,
            "fechaFin" as vencimiento,
            "fechaComienzo" as comienzo
        FROM "Cuota"
        WHERE dni = $1
        ORDER BY "fechaFin" DESC;
        """
        cuotas_db = await conn.fetch(query, dni_alumno)

        # Procesamos la respuesta para traducir el mes
        cuotas_procesadas = []
        for row in cuotas_db:
            datos_cuota = dict(row)
            # Obtenemos el nombre del mes en inglés y lo traducimos
            mes_en_ingles = datos_cuota.get("mes")
            if mes_en_ingles in meses_es:
                datos_cuota["mes"] = meses_es[mes_en_ingles]
            cuotas_procesadas.append(CuotaResponseAlumnoAuth(**datos_cuota))
            
        return cuotas_procesadas
    except Exception as e:
        raise DatabaseException("obtener cuotas del alumno", str(e))

# Obtiene las cuotas de UN SOLO alumno (Staff, buscando por DNI)
async def obtener_cuotas_por_dni(conn: Connection, dni: str) -> List[CuotaResponsePorDNI]:
    """
    Obtiene todas las cuotas de un alumno específico por su DNI.
    """
    try:
        # Primero, verificamos que la persona (alumno) exista
        persona_existe = await conn.fetchval(
            'SELECT 1 FROM "Persona" WHERE dni = $1', dni
        )
        if not persona_existe:
            raise NotFoundException("Alumno", dni)

        # Si existe, buscamos sus cuotas
        query = """
            SELECT
                "idCuota",
                dni,
                pagada,
                monto,
                "fechaComienzo",
                "fechaFin" as vencimiento,
                mes,
                EXTRACT(YEAR FROM "fechaFin")::INTEGER as anio,
                "nombreTrabajo" as trabajo,
                "nombreSuscripcion" as suscripcion
            FROM "Cuota"
            WHERE dni = $1
            ORDER BY "fechaComienzo" DESC;
        """
        
        resultados = await conn.fetch(query, dni)
        
        # Mapeamos los resultados al schema Pydantic
        return [CuotaResponsePorDNI(**dict(row)) for row in resultados]

    except NotFoundException:
        raise # Re-lanzamos la excepción para que el endpoint la maneje
    except Exception as e:
        raise DatabaseException("obtener cuotas por DNI", str(e))


async def modificar_cuota(conn: Connection, id_cuota: int, cuota_data: CuotaUpdateRequest) -> bool:
    """
    Actualiza todos los datos de una cuota.
    - Si pagada == False: Limpia (NULL) fechaDePago, horaDePago y metodoDePago.
    - Si pagada == True: Actualiza metodoDePago, pero no toca fechaDePago/horaDePago (mantiene lo que había).
    """
    try:
        # 1. Verificar si la cuota existe
        exists = await conn.fetchval('SELECT 1 FROM "Cuota" WHERE "idCuota" = $1', id_cuota)
        if not exists:
            raise NotFoundException("Cuota", id_cuota)

        # 2. Definir la query base
        # Actualizamos los campos "normales"
        # Mapeamos: vencimiento -> fechaFin, trabajo -> nombreTrabajo, suscripcion -> nombreSuscripcion
        
        if not cuota_data.pagada:
            # CASO 1: La cuota pasa a NO PAGADA (o se confirma como tal).
            # REGLA: Borrar rastros de pago.
            query = """
                UPDATE "Cuota"
                SET 
                    dni = $2,
                    pagada = $3,
                    monto = $4,
                    mes = $5,
                    "nombreTrabajo" = $6,
                    "nombreSuscripcion" = $7,
                    "fechaComienzo" = $8,
                    "fechaFin" = $9,
                    "idFacturacion" = $10,
                    -- Campos que se limpian
                    "metodoDePago" = NULL,
                    "fechaDePago" = NULL,
                    "horaDePago" = NULL
                WHERE "idCuota" = $1
            """
            await conn.execute(
                query,
                id_cuota,
                cuota_data.dni,
                cuota_data.pagada,
                cuota_data.monto,
                cuota_data.mes,
                cuota_data.trabajo,
                cuota_data.suscripcion,
                cuota_data.fechaComienzo,
                cuota_data.vencimiento, # Mapeado a fechaFin
                cuota_data.idFacturacion
            )
            
        else:
            # CASO 2: La cuota es PAGADA.
            # REGLA: Actualizamos datos básicos y metodoDePago. NO tocamos fechaDePago/horaDePago (para no perder el historial si ya estaba pagada).
            # Si quisieras establecer la fecha de pago al momento de esta edición, avísame, pero por defecto "modificar" suele respetar el dato histórico.
            query = """
                UPDATE "Cuota"
                SET 
                    dni = $2,
                    pagada = $3,
                    monto = $4,
                    mes = $5,
                    "nombreTrabajo" = $6,
                    "nombreSuscripcion" = $7,
                    "fechaComienzo" = $8,
                    "fechaFin" = $9,
                    "idFacturacion" = $10,
                    "metodoDePago" = $11
                WHERE "idCuota" = $1
            """
            await conn.execute(
                query,
                id_cuota,
                cuota_data.dni,
                cuota_data.pagada,
                cuota_data.monto,
                cuota_data.mes,
                cuota_data.trabajo,
                cuota_data.suscripcion,
                cuota_data.fechaComienzo,
                cuota_data.vencimiento,
                cuota_data.idFacturacion,
                cuota_data.metodoDePago
            )

        return True

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("modificar cuota", str(e))


async def eliminar_cuota(conn: Connection, id_cuota: int) -> bool:
    """
    Elimina físicamente una cuota de la base de datos dado su ID.
    """
    try:
        # Ejecutamos la sentencia DELETE
        # conn.execute devuelve un string tipo "DELETE 1" si tuvo éxito
        result = await conn.execute('DELETE FROM "Cuota" WHERE "idCuota" = $1', id_cuota)
        
        # Verificamos si realmente se borró algo (DELETE 0 significa que no existía)
        if result == "DELETE 0":
            raise NotFoundException("Cuota", id_cuota)
            
        return True

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("eliminar cuota", str(e))


async def generar_cuotas_masivas_mensuales(conn: Connection) -> int:
    """
    Genera automáticamente las cuotas para TODOS los alumnos activos.
    Se han agregado casteos explícitos (::DATE, ::VARCHAR, ::INTEGER) para evitar conflictos de tipos.
    """
    try:
        hoy = date.today()
        vencimiento = hoy + timedelta(days=30)
        
        # Nombre del mes
        nombre_mes = calendar.month_name[hoy.month].capitalize()
        meses_trad = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }
        if nombre_mes in meses_trad:
            nombre_mes = meses_trad[nombre_mes]

        anio_actual = hoy.year

        # --- QUERY CORREGIDA CON CASTEOS ---
        query = """
        INSERT INTO "Cuota" (
            dni, 
            pagada, 
            monto, 
            "fechaComienzo", 
            "fechaFin", 
            mes, 
            "nombreTrabajo", 
            "nombreSuscripcion"
        )
        SELECT 
            a.dni,
            FALSE as pagada,
            s.precio as monto,
            $1::DATE as "fechaComienzo",  -- Casteo explícito a DATE
            $2::DATE as "fechaFin",       -- Casteo explícito a DATE
            $3::VARCHAR as mes,           -- Casteo explícito a VARCHAR (soluciona tu error)
            a."nombreTrabajo",
            a."nombreSuscripcion"
        FROM "Alumno" a
        JOIN "AlumnoActivo" aa ON a.dni = aa.dni
        JOIN "Suscripcion" s ON a."nombreSuscripcion" = s."nombreSuscripcion"
        WHERE NOT EXISTS (
            SELECT 1 FROM "Cuota" c 
            WHERE c.dni = a.dni 
            AND c.mes = $3::VARCHAR       -- Usamos el mismo casteo aquí
            AND EXTRACT(YEAR FROM c."fechaFin") = $4::INTEGER -- Casteo explícito a INTEGER
        );
        """

        resultado = await conn.execute(query, hoy, vencimiento, nombre_mes, anio_actual)
        
        filas_insertadas = int(resultado.split(" ")[-1])
        
        print(f"--- [AUTOMATIZACIÓN] Se generaron {filas_insertadas} cuotas nuevas para el mes de {nombre_mes}. ---")
        return filas_insertadas

    except Exception as e:
        print(f"Error generando cuotas masivas: {e}")
        return 0

