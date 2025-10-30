# src/services/estadisticasService.py

from asyncpg import Connection
from typing import List

from schemas.estadisticasSchema import (
    EstadisticaTrabajoData,
    EstadisticaTrabajoItem
)

from utils.exceptions import DatabaseException

async def obtener_alumnos_por_trabajo(conn: Connection) -> List[EstadisticaTrabajoItem]:
    """
    Calcula la cantidad de alumnos inscritos en cada tipo de trabajo.
    """
    try:
        query = """
        SELECT
            t."nombreTrabajo" as nombre,
            COUNT(a.dni)::INTEGER as cantidad
        FROM "Trabajo" t
        LEFT JOIN "Alumno" a ON t."nombreTrabajo" = a."nombreTrabajo"
        GROUP BY t."nombreTrabajo"
        ORDER BY cantidad DESC, nombre ASC;
        """
        
        resultados_db = await conn.fetch(query)
        
        # Formateamos la respuesta según el esquema requerido
        respuesta_formateada = []
        for i, row in enumerate(resultados_db):
            # Creamos el objeto interno 'data'
            data_item = EstadisticaTrabajoData(nombre=row['nombre'], cantidad=row['cantidad'])
            # Creamos el objeto principal con 'id' y 'data'
            item_respuesta = EstadisticaTrabajoItem(id=i + 1, data=[data_item])
            respuesta_formateada.append(item_respuesta)
            
        return respuesta_formateada

    except Exception as e:
        raise DatabaseException("obtener estadísticas de alumnos por trabajo", str(e))