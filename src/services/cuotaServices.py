
from asyncpg import Connection
from typing import List

from schemas.cuotaSchema import (
    CuotaResponse
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

async def obtener_cuotas_por_alumno(conn: Connection, dni_alumno: str) -> List[CuotaResponse]:
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
            cuotas_procesadas.append(CuotaResponse(**datos_cuota))
            
        return cuotas_procesadas
    except Exception as e:
        raise DatabaseException("obtener cuotas del alumno", str(e))

async def obtener_cuotas_por_dni(conn: Connection, dni: str) -> List[CuotaResponse]:
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
                "fechaFin",
                mes,
                "nombreTrabajo",
                "nombreSuscripcion"
            FROM "Cuota"
            WHERE dni = $1
            ORDER BY "fechaComienzo" DESC;
        """
        
        resultados = await conn.fetch(query, dni)
        
        # Mapeamos los resultados al schema Pydantic
        return [CuotaResponse(**dict(row)) for row in resultados]

    except NotFoundException:
        raise # Re-lanzamos la excepción para que el endpoint la maneje
    except Exception as e:
        raise DatabaseException("obtener cuotas por DNI", str(e))
