from asyncpg import Connection
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from schemas.facturacionSchema import FacturacionResponse, ReporteFacturacion, DetalleCuotaFactura

async def generar_cierre_quincenal(conn: Connection, fecha_inicio: date, fecha_fin: date) -> List[FacturacionResponse]:
    """
    Genera el cierre de facturación agrupado por Titular.
    Utiliza una CTE para asegurar que cada alumno tenga un único titular asignado
    y evitar la duplicación de cuotas en el cálculo.
    """
    
    # 1. Query Optimizada: Primero define el titular por alumno, luego busca las cuotas.
    query_busqueda = """
        WITH "TitularAsignado" AS (
            SELECT DISTINCT ON (asiste.dni)
                asiste.dni,
                p.nombre || ' ' || p.apellido as nombre_titular
            FROM "Asiste" asiste
            INNER JOIN "Pertenece" pert ON asiste."nroGrupo" = pert."nroGrupo"
            INNER JOIN "Persona" p ON pert."dniEmpleado" = p.dni
            WHERE pert."dniEmpleado" IS NOT NULL
        )
        SELECT 
            c."idCuota",
            c.monto,
            COALESCE(ta.nombre_titular, 'Administración') as nombre_titular
        FROM "Cuota" c
        LEFT JOIN "TitularAsignado" ta ON c.dni = ta.dni
        WHERE c."fechaDePago" BETWEEN $1 AND $2
            AND c.pagada = True 
            AND c.facturado = False
    """

    async with conn.transaction():
        rows = await conn.fetch(query_busqueda, fecha_inicio, fecha_fin)

        if not rows:
            return []

        # 2. Agrupar en memoria
        agrupado = {}
        for row in rows:
            titular = row['nombre_titular']
            monto = row['monto'] # Viene como Decimal
            cuota_id = row['idCuota']

            if titular not in agrupado:
                agrupado[titular] = {
                    'montoTotal': Decimal(0), # Importante inicializar como Decimal
                    'cantidadCuotas': 0, 
                    'ids': []
                }
            
            agrupado[titular]['montoTotal'] += monto
            agrupado[titular]['cantidadCuotas'] += 1
            agrupado[titular]['ids'].append(cuota_id)

        facturas_generadas = []
        fecha_generacion = datetime.now()

        # 3. Insertar facturas y actualizar cuotas
        for titular, datos in agrupado.items():
            # A. Insertar cabecera de Factura
            insert_factura = """
                INSERT INTO "Facturacion" 
                ("fechaInicio", "fechaFin", "fechaGeneracion", "montoTotal", "cantidadCuotas", "titular")
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING "idFacturacion", "fechaInicio", "fechaFin", "fechaGeneracion", "montoTotal", "cantidadCuotas", "titular"
            """
            
            factura_row = await conn.fetchrow(
                insert_factura, 
                fecha_inicio, 
                fecha_fin, 
                fecha_generacion, 
                datos['montoTotal'], 
                datos['cantidadCuotas'],
                titular
            )
            
            id_facturacion = factura_row['idFacturacion']

            # B. Actualizar Cuotas (Vinculando ID de factura)
            if datos['ids']:
                update_cuotas = """
                    UPDATE "Cuota"
                    SET facturado = True,
                        "idFacturacion" = $1
                    WHERE "idCuota" = ANY($2::int[])
                """
                await conn.execute(update_cuotas, id_facturacion, datos['ids'])

            facturas_generadas.append(FacturacionResponse(**dict(factura_row)))

        return facturas_generadas

async def obtener_reporte_por_id(conn: Connection, id_facturacion: int) -> Optional[ReporteFacturacion]:
    """
    Obtiene la factura y el detalle de cuotas asociadas.
    """
    # 1. Cabecera
    query_factura = """
        SELECT "idFacturacion", "fechaInicio", "fechaFin", "fechaGeneracion", "montoTotal", "cantidadCuotas", "titular"
        FROM "Facturacion"
        WHERE "idFacturacion" = $1
    """
    factura_row = await conn.fetchrow(query_factura, id_facturacion)
    
    if not factura_row:
        return None

    # 2. Detalles (Joins para traer nombre alumno y concepto)
    query_detalles = """
        SELECT 
            c."idCuota",
            c.dni,
            p.nombre || ' ' || p.apellido as alumno,
            c.monto,
            c."fechaDePago" as "fechaPago",
            c."metodoDePago",
            c.mes || ' - ' || c."nombreSuscripcion" as concepto
        FROM "Cuota" c
        INNER JOIN "Persona" p ON c.dni = p.dni
        WHERE c."idFacturacion" = $1
    """
    detalles_rows = await conn.fetch(query_detalles, id_facturacion)

    detalles = [DetalleCuotaFactura(**dict(row)) for row in detalles_rows]
    datos_factura = dict(factura_row)
    
    return ReporteFacturacion(**datos_factura, detalles=detalles)

