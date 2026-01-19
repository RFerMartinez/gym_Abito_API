from asyncpg import Connection
from datetime import date
from utils.exceptions import DatabaseException

async def generar_cierre_quincenal(conn: Connection, fecha_inicio: date, fecha_fin: date):
    async with conn.transaction():
        # 1. Buscar cuotas pagadas por medios digitales que no estén facturadas
        query_buscar = """
            SELECT "idCuota", monto 
            FROM "Cuota" 
            WHERE pagada = TRUE 
                AND "metodoDePago" IN ('qr', 'transferencia')
                AND "idFacturacion" IS NULL
                AND "fechaDePago" BETWEEN $1 AND $2
        """
        cuotas_pendientes = await conn.fetch(query_buscar, fecha_inicio, fecha_fin)
        
        if not cuotas_pendientes:
            return None

        total_monto = sum(c['monto'] for c in cuotas_pendientes)
        total_cuotas = len(cuotas_pendientes)

        # 2. Crear el registro en la tabla Facturacion
        query_fact = """
            INSERT INTO "Facturacion" ("fechaInicio", "fechaFin", "montoTotal", "cantidadCuotas")
            VALUES ($1, $2, $3, $4)
            RETURNING "idFacturacion"
        """
        id_fact = await conn.fetchval(query_fact, fecha_inicio, fecha_fin, total_monto, total_cuotas)

        # 3. Vincular las cuotas al lote de facturación
        ids_cuotas = [c['idCuota'] for c in cuotas_pendientes]
        query_vincular = """
            UPDATE "Cuota" 
            SET "idFacturacion" = $1 
            WHERE "idCuota" = ANY($2)
        """
        await conn.execute(query_vincular, id_fact, ids_cuotas)
        
        return id_fact

async def obtener_reporte_facturacion(conn: Connection, id_facturacion: int):
    query = """
        SELECT 
            p.nombre || ' ' || p.apellido as alumno,
            p.dni,
            c.monto,
            c."fechaDePago" as "fechaPago",
            c."metodoDePago"
        FROM "Cuota" c
        JOIN "Persona" p ON c.dni = p.dni
        WHERE c."idFacturacion" = $1
    """
    return await conn.fetch(query, id_facturacion)