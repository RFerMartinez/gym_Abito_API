
from datetime import date
from asyncpg import Connection
from typing import List
from dateutil.relativedelta import relativedelta

from schemas.estadisticasSchema import (
    DashboardKPIs,
    DatasetTurno,
    EntrenadorStats,
    EstadisticaTrabajoData,
    EstadisticaTrabajoItem,
    GraficoTurnosResponse
)

from utils.exceptions import DatabaseException, NotFoundException

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

# Helper para obtener nombre del mes en español (ajusta según tu BD)
def obtener_nombre_mes_actual():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual_idx = date.today().month - 1
    return meses[mes_actual_idx]

async def obtener_kpis_generales(conn: Connection) -> DashboardKPIs:
    try:
        hoy = date.today()
        
        # Variables para filtros numéricos (más robusto que el string "Diciembre")
        mes_actual = hoy.month
        anio_actual = hoy.year

        # ---------------------------------------------------------
        # 1. ALUMNOS ACTIVOS
        # ---------------------------------------------------------
        query_activos = 'SELECT COUNT(*) FROM "AlumnoActivo"'
        alumnos_activos = await conn.fetchval(query_activos)

        # ---------------------------------------------------------
        # 2. CUOTAS VENCIDAS (Cantidad y Monto Total)
        # ---------------------------------------------------------
        # Condición: No pagadas Y fechaFin menor a hoy
        query_vencidas_data = '''
            SELECT COUNT(*) as cantidad, COALESCE(SUM(monto), 0) as total
            FROM "Cuota" 
            WHERE pagada = FALSE AND "fechaFin" < $1
        '''
        res_vencidas = await conn.fetchrow(query_vencidas_data, hoy)
        cant_vencidas = res_vencidas['cantidad']
        monto_vencidas = float(res_vencidas['total'])

        # ---------------------------------------------------------
        # 3. INGRESOS / RECAUDACIÓN (Monto)
        # ---------------------------------------------------------
        # Cuotas pagadas efectivamente en este mes (por fechaDePago)
        query_cobrado = '''
            SELECT COALESCE(SUM(monto), 0) 
            FROM "Cuota" 
            WHERE pagada = TRUE 
                AND EXTRACT(MONTH FROM "fechaDePago") = $1
                AND EXTRACT(YEAR FROM "fechaDePago") = $2
        '''
        cantidad_cobrado = await conn.fetchval(query_cobrado, mes_actual, anio_actual)
        ingreso_mensual = cantidad_cobrado 

        # ---------------------------------------------------------
        # 4. PORCENTAJE DE COBRO
        # ---------------------------------------------------------
        
        # A) DENOMINADOR: Cuotas Generadas este mes
        # Usamos 'fechaComienzo' en lugar de la columna 'mes' para evitar problemas de idioma
        query_generadas = '''
            SELECT COUNT(*) 
            FROM "Cuota" 
            WHERE EXTRACT(MONTH FROM "fechaComienzo") = $1
                AND EXTRACT(YEAR FROM "fechaComienzo") = $2
        '''
        total_generadas = await conn.fetchval(query_generadas, mes_actual, anio_actual)

        # B) NUMERADOR: Cuotas Pagadas este mes (Recaudación)
        query_pagadas_mes_actual = '''
            SELECT COUNT(*) 
            FROM "Cuota" 
            WHERE pagada = TRUE 
                AND EXTRACT(MONTH FROM "fechaDePago") = $1 
                AND EXTRACT(YEAR FROM "fechaDePago") = $2
        '''
        total_pagadas_este_mes = await conn.fetchval(query_pagadas_mes_actual, mes_actual, anio_actual)

        porcentaje = 0.0
        if total_generadas > 0:
            porcentaje = round((total_pagadas_este_mes / total_generadas) * 100, 2)

        return DashboardKPIs(
            alumnos_activos=alumnos_activos,
            cuotas_vencidas=cant_vencidas,
            monto_cuotas_vencidas=monto_vencidas,
            ingreso_mensual=float(ingreso_mensual),
            cantidad_cobrado=float(cantidad_cobrado),
            porcentaje_cobro=porcentaje
        )

    except Exception as e:
        raise DatabaseException("Error al calcular KPIs del dashboard", str(e))


async def obtener_alumnos_por_turno_mensual(conn: Connection) -> GraficoTurnosResponse:
    try:
        hoy = date.today()
        
        # --- 1. Calcular fecha de inicio (hace 6 meses) MANUALMENTE ---
        # Restamos meses manejando el cambio de año
        mes_inicio = hoy.month - 6
        anio_inicio = hoy.year
        if mes_inicio <= 0:
            mes_inicio += 12
            anio_inicio -= 1
        
        fecha_inicio = date(anio_inicio, mes_inicio, 1)
        
        # --- 2. Generar etiquetas y keys para los últimos 7 meses ---
        nombres_meses = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }
        
        labels = []
        meses_keys = []
        
        # Iteramos desde la fecha de inicio avanzando mes a mes
        curr_m = mes_inicio
        curr_y = anio_inicio
        
        for _ in range(7):
            labels.append(nombres_meses[curr_m])
            meses_keys.append((curr_y, curr_m))
            
            # Avanzar al siguiente mes
            curr_m += 1
            if curr_m > 12:
                curr_m = 1
                curr_y += 1

        # Inicializar contadores
        data_manana = [0] * 7
        data_tarde = [0] * 7

        # --- 3. Consulta SQL CORREGIDA ---
        # El GROUP BY ahora usa las expresiones completas para evitar el error de Postgres
        query = """
            SELECT 
                EXTRACT(YEAR FROM c."fechaComienzo")::int as anio,
                EXTRACT(MONTH FROM c."fechaComienzo")::int as mes,
                MIN(h."horaInicio") as hora_inicio,
                c.dni
            FROM "Cuota" c
            JOIN "Asiste" a ON c.dni = a.dni
            JOIN "Horario" h ON a."nroGrupo" = h."nroGrupo"
            WHERE c."fechaComienzo" >= $1
            GROUP BY 
                EXTRACT(YEAR FROM c."fechaComienzo"), 
                EXTRACT(MONTH FROM c."fechaComienzo"), 
                c.dni
        """
        
        rows = await conn.fetch(query, fecha_inicio)

        # --- 4. Procesar resultados ---
        for row in rows:
            key = (row['anio'], row['mes'])
            
            if key in meses_keys:
                idx = meses_keys.index(key)
                
                # Turno Mañana < 13:00, Tarde >= 13:00
                hora = row['hora_inicio']
                if hora.hour < 13:
                    data_manana[idx] += 1
                else:
                    data_tarde[idx] += 1

        return GraficoTurnosResponse(
            labels=labels,
            datasets=[
                DatasetTurno(
                    label="Mañana",
                    data=data_manana,
                    backgroundColor="rgba(210, 214, 222, 0.8)",
                    borderColor="rgba(210, 214, 222, 1)"
                ),
                DatasetTurno(
                    label="Tarde",
                    data=data_tarde,
                    backgroundColor="rgba(0, 192, 239, 0.8)",
                    borderColor="rgba(0, 192, 239, 1)"
                )
            ]
        )
    except Exception as e:
        # Imprimir error en consola del backend para debug fácil
        print(f"DEBUG ERROR: {str(e)}")
        raise DatabaseException("Error al calcular gráfico de turnos", str(e))


async def obtener_estadisticas_entrenador(conn: Connection, dni_empleado: str) -> EntrenadorStats:
    """
    Calcula métricas específicas para el entrenador/staff logueado:
    1. Datos personales.
    2. Alumnos únicos que asisten a sus grupos.
    3. Recaudación de ESOS alumnos en el mes actual.
    4. Deudas pendientes de ESOS alumnos.
    """
    try:
        hoy = date.today()
        mes_actual = hoy.month
        anio_actual = hoy.year

        # 1. Obtener datos básicos del Empleado (unimos Persona y Empleado para sacar el Rol)
        query_empleado = '''
            SELECT p.nombre, p.apellido, e.dni, e.rol
            FROM "Empleado" e
            JOIN "Persona" p ON e.dni = p.dni
            WHERE e.dni = $1
        '''
        empleado = await conn.fetchrow(query_empleado, dni_empleado)
        
        if not empleado:
            # Si no es empleado (ej: es Admin puro sin registro en tabla Empleado, aunque tu lógica los crea),
            # devolvemos datos vacíos o buscamos solo en Persona.
            # Asumiremos que existe en Empleado o Persona.
            raise NotFoundException("Empleado", dni_empleado)

        # 2. Identificar a los alumnos a cargo (Subquery reutilizable)
        # Un alumno está "a cargo" si asiste a un grupo (Pertenece) donde el dniEmpleado es el del usuario.
        subquery_mis_alumnos = '''
            SELECT DISTINCT a.dni
            FROM "Asiste" a
            JOIN "Pertenece" p ON a."nroGrupo" = p."nroGrupo" AND a.dia = p.dia
            WHERE p."dniEmpleado" = $1
        '''

        # A) Cantidad de Alumnos a Cargo
        query_cant_alumnos = f'''
            SELECT COUNT(*) FROM ({subquery_mis_alumnos}) as mis_alumnos
        '''
        alumnos_a_cargo = await conn.fetchval(query_cant_alumnos, dni_empleado)

        # B) Monto Recaudado (Mes Actual) de MIS alumnos
        # Sumamos las cuotas pagadas este mes, pero SOLO de los DNIs que me pertenecen
        query_recaudado = f'''
            SELECT COALESCE(SUM(c.monto), 0)
            FROM "Cuota" c
            WHERE c.pagada = TRUE
                AND EXTRACT(MONTH FROM c."fechaDePago") = $2
                AND EXTRACT(YEAR FROM c."fechaDePago") = $3
                AND c.dni IN ({subquery_mis_alumnos})
        '''
        monto_recaudado = await conn.fetchval(query_recaudado, dni_empleado, mes_actual, anio_actual)

        # C) Cuotas Pendientes de MIS alumnos
        # Contamos todas las cuotas impagas de mis alumnos (históricas)
        query_pendientes = f'''
            SELECT COUNT(*)
            FROM "Cuota" c
            WHERE c.pagada = FALSE
                AND c.dni IN ({subquery_mis_alumnos})
        '''
        cuotas_pendientes = await conn.fetchval(query_pendientes, dni_empleado)

        return EntrenadorStats(
            nombre=empleado['nombre'],
            apellido=empleado['apellido'],
            dni=empleado['dni'],
            rol=empleado['rol'],
            alumnos_a_cargo=alumnos_a_cargo,
            monto_recaudado_mes=float(monto_recaudado),
            cuotas_pendientes=cuotas_pendientes
        )

    except Exception as e:
        # Si el error es NotFound, lo dejamos pasar, sino es de BD
        if "NotFound" in str(e): raise
        raise DatabaseException("Error al calcular estadísticas de entrenador", str(e))

async def obtener_stats_todos_empleados(conn: Connection) -> List[EntrenadorStats]:
    """
    Obtiene las estadísticas de rendimiento para TODOS los empleados registrados.
    """
    try:
        # 1. Obtener lista de todos los empleados
        query_empleados = '''
            SELECT e.dni 
            FROM "Empleado" e
            JOIN "Persona" p ON e.dni = p.dni
            ORDER BY p.apellido, p.nombre
        '''
        empleados_rows = await conn.fetch(query_empleados)
        
        lista_stats = []
        
        # 2. Iterar y calcular stats por cada uno
        # (Reutilizamos la lógica que diseñamos antes, pero encapsulada o inline)
        for row in empleados_rows:
            # Llamamos a la función individual para cada DNI
            # Nota: Esto hace varias queries. Si tienes 50 empleados podría ser lento,
            # pero para un gimnasio normal (5-10 profes) es perfectamente aceptable y más limpio.
            stats = await obtener_estadisticas_entrenador(conn, row['dni'])
            lista_stats.append(stats)
            
        return lista_stats

    except Exception as e:
        raise DatabaseException("Error listando stats de empleados", str(e))


