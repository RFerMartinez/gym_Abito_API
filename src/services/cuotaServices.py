
from asyncpg import Connection
from typing import List

from schemas.cuotaSchema import (
    CuotaResponse
)
from utils.exceptions import (
    DatabaseException
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
            "fechaFin" as vencimiento
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

