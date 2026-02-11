# src/services/facturacionServices.py

from asyncpg import Connection
from datetime import date, datetime, timedelta
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
    Toma TODAS las cuotas que estén pagadas y no facturadas (QR o Transferencia),
    sin importar la fecha en que se realizó el pago.
    """
    
    # Query modificada: Se eliminó la condición 'c."fechaDePago" BETWEEN $1 AND $2'
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
        WHERE c.pagada = True 
            AND c.facturado = False
            AND c."metodoDePago" IN ('qr', 'transferencia')
    """

    async with conn.transaction():
        # Ya no pasamos fechas al fetch porque no se usan en el WHERE
        rows = await conn.fetch(query_busqueda)

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
            # Las fechas inicio/fin se guardan solo como referencia del periodo administrativo
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
    Obtiene el reporte completo de una facturación específica y sus detalles,
    incluyendo la hora de pago para el nuevo formato de PDF.
    """
    # 1. Cabecera (Se mantiene igual)
    query_factura = """
        SELECT "idFacturacion", "fechaInicio", "fechaFin", "fechaGeneracion", "montoTotal", "cantidadCuotas", "titular"
        FROM "Facturacion"
        WHERE "idFacturacion" = $1
    """
    factura_row = await conn.fetchrow(query_factura, id_facturacion)
    
    if not factura_row:
        return None

    # 2. Detalles: Se agregó la columna "horaDePago"
    query_detalles = """
        SELECT 
            c."idCuota",
            c.dni,
            p.nombre || ' ' || p.apellido as alumno,
            c.monto,
            c."fechaDePago" as "fechaPago",
            c."horaDePago", -- Agregado para el reporte
            c."metodoDePago",
            c.mes || ' - ' || c."nombreSuscripcion" as concepto
        FROM "Cuota" c
        INNER JOIN "Persona" p ON c.dni = p.dni
        WHERE c."idFacturacion" = $1
    """
    detalles_rows = await conn.fetch(query_detalles, id_facturacion)

    # Convertimos a objetos Pydantic (Asegúrate de que DetalleCuotaFactura en schemas acepte horaDePago)
    detalles = [DetalleCuotaFactura(**dict(row)) for row in detalles_rows]

    # 3. Construir respuesta
    datos_factura = dict(factura_row)
    return ReporteFacturacion(**datos_factura, detalles=detalles)

def generar_pdf_reporte(reporte: ReporteFacturacion) -> bytes:
    """
    Genera un PDF con diseño técnico minimalista basado en los datos del reporte.
    Retorna los bytes del PDF con metadatos de título corregidos.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm, 
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    
    # Formateamos las fechas para el título interno
    f_inicio = reporte.fechaInicio.strftime("%d/%m/%Y")
    f_fin = reporte.fechaFin.strftime("%d/%m/%Y")
    titulo_metadato = f"ReporteFacturacion ({f_inicio} - {f_fin})"

    # --- Función interna para fijar el título en el canvas ---
    def fijar_metadatos(canvas, doc):
        canvas.setTitle(titulo_metadato)
        canvas.setAuthor("Gimnasio Abito")

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
    info_data = [
        [f"TITULAR: {reporte.titular.upper()}", ""],
        [f"PERIODO: {f_inicio} - {f_fin}", f"TOTAL CUOTAS: {reporte.cantidadCuotas}"],
        [f"MONTO TOTAL :", f"$ {reporte.montoTotal:,.2f}"]
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
    headers = ["FECHA", "HORA", "CONCEPTO", "MÉTODO", "MONTO"]
    data_tabla = [headers]
    
    for det in reporte.detalles:
        fecha_fmt = det.fechaPago.strftime("%d/%m/%Y") if det.fechaPago else "-"
        
        hora_fmt = "-"
        if hasattr(det, 'horaDePago') and det.horaDePago:
            try:
                hora_fmt = det.horaDePago.strftime("%H:%M:%S")
            except AttributeError:
                hora_fmt = str(det.horaDePago)
        
        row = [
            fecha_fmt,
            hora_fmt,
            det.concepto[:35],
            det.metodoDePago.upper() if det.metodoDePago else "-",
            f"$ {det.monto:,.0f}"
        ]
        data_tabla.append(row)

    col_widths = [3*cm, 2.5*cm, 7.5*cm, 2.5*cm, 2.5*cm]
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
        ('ALIGN', (-1,1), (-1,-1), 'RIGHT'),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.lightgrey),
    ])
    
    t_detalles.setStyle(style_tabla)
    elements.append(t_detalles)

    # --- CAMBIO CLAVE ---
    # Pasamos la función fijar_metadatos a onFirstPage
    doc.build(elements, onFirstPage=fijar_metadatos)
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

async def obtener_todas_facturaciones(conn: Connection) -> List[FacturacionResponse]:
    """
    Recupera el historial completo de facturaciones realizadas.
    Ordenado por fecha de generación descendente.
    """
    query = """
        SELECT 
            "idFacturacion", 
            "fechaInicio", 
            "fechaFin", 
            "fechaGeneracion", 
            "montoTotal", 
            "cantidadCuotas", 
            "titular"
        FROM "Facturacion"
        ORDER BY "fechaGeneracion" DESC
    """
    
    rows = await conn.fetch(query)
    
    # Convertimos cada fila en un objeto Pydantic
    return [FacturacionResponse(**dict(row)) for row in rows]

async def procesar_cierre_automatico(conn: Connection):
    """
    Determina el periodo a cerrar basándose en la fecha actual y ejecuta el cierre.
    Se espera que esta función corra los días 1 y 15.
    """
    hoy = date.today()
    fecha_inicio = None
    fecha_fin = None

    # Lógica de Fechas
    if hoy.day == 1:
        # Caso: Es día 1. Cerramos la quincena del mes ANTERIOR (día 16 al fin de mes).
        # Restamos 1 día para volver al mes pasado
        ultimo_dia_mes_anterior = hoy - timedelta(days=1)
        fecha_fin = ultimo_dia_mes_anterior
        fecha_inicio = date(ultimo_dia_mes_anterior.year, ultimo_dia_mes_anterior.month, 16)
        
    elif hoy.day == 15:
        # Caso: Es día 15. Cerramos la primera quincena del mes ACTUAL (día 1 al 15).
        fecha_inicio = date(hoy.year, hoy.month, 1)
        fecha_fin = hoy
    else:
        # Por seguridad, si el scheduler corre otro día, no hacemos nada o asumimos manual
        print(f"[Facturacion Auto] Ejecución en día no estándar ({hoy.day}). Se omitirá.")
        return

    print(f"[Facturacion Auto] Procesando cierre para periodo: {fecha_inicio} al {fecha_fin}")

    try:
        # Llamamos a la función que ya creamos antes
        reportes = await generar_cierre_quincenal(conn, fecha_inicio, fecha_fin)
        
        if reportes:
            print(f"[Facturacion Auto] Cierre exitoso. {len(reportes)} facturas generadas.")
        else:
            print("[Facturacion Auto] No hubo movimientos para facturar en este periodo.")
            
    except Exception as e:
        print(f"[Facturacion Auto] Error crítico: {str(e)}")


