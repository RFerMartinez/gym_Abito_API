# src/services/facturacionServices.py

from asyncpg import Connection
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from io import BytesIO

# Imports para PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from schemas.facturacionSchema import FacturacionResponse, ReporteFacturacion, DetalleCuotaFactura

async def generar_cierre_quincenal(conn: Connection, fecha_inicio: date, fecha_fin: date) -> List[FacturacionResponse]:
    """
    Genera el cierre de facturación agrupado por Titular.
    SOLO incluye pagos por 'qr' o 'transferencia'.
    Excluye explícitamente los pagos en 'efectivo'.
    """
    
    # Query filtrada por método de pago
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
          AND c."metodoDePago" IN ('qr', 'transferencia')  -- <--- FILTRO AGREGADO
    """

    async with conn.transaction():
        rows = await conn.fetch(query_busqueda, fecha_inicio, fecha_fin)

        if not rows:
            return []

        # Agrupar en memoria
        agrupado = {}
        for row in rows:
            titular = row['nombre_titular']
            monto = row['monto']
            cuota_id = row['idCuota']

            if titular not in agrupado:
                agrupado[titular] = {
                    'montoTotal': Decimal(0), 
                    'cantidadCuotas': 0, 
                    'ids': []
                }
            
            agrupado[titular]['montoTotal'] += monto
            agrupado[titular]['cantidadCuotas'] += 1
            agrupado[titular]['ids'].append(cuota_id)

        facturas_generadas = []
        fecha_generacion = datetime.now()

        # Insertar facturas y actualizar cuotas
        for titular, datos in agrupado.items():
            # A. Insertar Factura
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

            # B. Actualizar Cuotas
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
    Obtiene el reporte completo de una facturación específica y sus detalles.
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

    # 2. Detalles
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

    # 3. Construir respuesta
    datos_factura = dict(factura_row)
    return ReporteFacturacion(**datos_factura, detalles=detalles)

def generar_pdf_reporte(reporte: ReporteFacturacion) -> bytes:
    """
    Genera un PDF con diseño técnico minimalista basado en los datos del reporte.
    Retorna los bytes del PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm, 
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()

    # --- 1. Encabezado Minimalista ---
    title_style = ParagraphStyle(
        'TechnicalTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        alignment=1, # Center
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph(f"REPORTE DE FACTURACIÓN #{reporte.idFacturacion}", title_style))
    elements.append(Spacer(1, 0.5*cm))

    # --- 2. Información General ---
    f_generacion = reporte.fechaGeneracion.strftime("%d/%m/%Y %H:%M")
    f_inicio = reporte.fechaInicio.strftime("%d/%m/%Y")
    f_fin = reporte.fechaFin.strftime("%d/%m/%Y")
    
    info_data = [
        [f"TITULAR: {reporte.titular.upper()}", f"GENERADO: {f_generacion}"],
        [f"PERIODO: {f_inicio} - {f_fin}", f"TOTAL CUOTAS: {reporte.cantidadCuotas}"],
        [f"MONTO TOTAL FACTURADO:", f"$ {reporte.montoTotal:,.2f}"]
    ]

    t_info = Table(info_data, colWidths=[10*cm, 8*cm])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('FONTNAME', (0,2), (0,2), 'Helvetica-Bold'),
        ('FONTNAME', (1,2), (1,2), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.darkgray),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 1*cm))

    # --- 3. Tabla de Detalles ---
    headers = ["ID", "FECHA", "ALUMNO", "DNI", "CONCEPTO", "MÉTODO", "MONTO"]
    data_tabla = [headers]
    
    for det in reporte.detalles:
        fecha_fmt = det.fechaPago.strftime("%d/%m") if det.fechaPago else "-"
        row = [
            str(det.idCuota),
            fecha_fmt,
            det.alumno[:20],
            det.dni,
            det.concepto[:25],
            det.metodoDePago.upper() if det.metodoDePago else "-",
            f"$ {det.monto:,.0f}"
        ]
        data_tabla.append(row)

    col_widths = [1.5*cm, 2*cm, 4*cm, 2.5*cm, 4.5*cm, 2*cm, 2*cm]
    t_detalles = Table(data_tabla, colWidths=col_widths)

    style_tabla = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.Color(0.9, 0.9, 0.9)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ALIGN', (0,1), (-1,-1), 'CENTER'),
        ('ALIGN', (2,1), (2,-1), 'LEFT'),
        ('ALIGN', (4,1), (4,-1), 'LEFT'),
        ('ALIGN', (-1,1), (-1,-1), 'RIGHT'),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.lightgrey),
    ])
    
    t_detalles.setStyle(style_tabla)
    elements.append(t_detalles)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

