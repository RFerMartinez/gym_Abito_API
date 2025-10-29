
from datetime import time, date, timedelta
from asyncpg import Connection
from typing import List, Optional

import calendar

from schemas.alumnoSchema import (
    AlumnoActivate,
    AlumnoActivateResponse,
    AlumnoListado,
    AlumnoDetalle,
    HorarioAlumno
)

from utils.exceptions import (
    NotFoundException,
    DuplicateEntryException,
    BusinessRuleException,
    DatabaseException
)

async def activar_alumno(conn: Connection, data: AlumnoActivate) -> AlumnoActivateResponse:
    """
    Servicio para activar una persona como alumno activo.
    Realiza las siguientes acciones en una transacción:
    1.  Verifica que la Persona exista y no sea ya un Alumno.
    2.  Verifica la existencia de Trabajo y Suscripción.
    3.  Inserta el registro en la tabla "Alumno".
    4.  Inserta el registro en la tabla "AlumnoActivo".
    5.  Verifica la capacidad y asigna los horarios en la tabla "Asiste".
    """
    async with conn.transaction():
        try:
            # 1. Verificar que la Persona existe
            persona = await conn.fetchrow('SELECT * FROM "Persona" WHERE dni = $1', data.dni)
            if not persona:
                raise NotFoundException("Persona", data.dni)

            # 2. Verificar que no sea ya un alumno
            es_alumno = await conn.fetchval('SELECT 1 FROM "Alumno" WHERE dni = $1', data.dni)
            if es_alumno:
                raise DuplicateEntryException("Alumno", data.dni)

            # 3. Validar FKs (Trabajo y Suscripcion)
            trabajo = await conn.fetchval('SELECT 1 FROM "Trabajo" WHERE "nombreTrabajo" = $1', data.nombreTrabajo)
            if not trabajo:
                raise NotFoundException("Trabajo", data.nombreTrabajo)
            
            suscripcion = await conn.fetchrow('SELECT precio FROM "Suscripcion" WHERE "nombreSuscripcion" = $1', data.nombreSuscripcion)
            if not suscripcion:
                raise NotFoundException("Suscripción", data.nombreSuscripcion)
            monto_cuota = suscripcion['precio']

            # 4. Insertar en Alumno
            await conn.execute('''
                INSERT INTO "Alumno" (dni, "nombreTrabajo", "nombreSuscripcion", nivel, deporte)
                VALUES ($1, $2, $3, $4, $5)
            ''', data.dni, data.nombreTrabajo, data.nombreSuscripcion, data.nivel, data.deporte)

            # 5. Insertar en AlumnoActivo
            await conn.execute('INSERT INTO "AlumnoActivo" (dni) VALUES ($1)', data.dni)

            # 6. Asignar horarios
            for horario in data.horarios:
                # Verificar capacidad del grupo en ese día
                query_capacidad = '''
                    SELECT p."capacidadMax", COUNT(a.dni) as inscritos
                    FROM "Pertenece" p
                    LEFT JOIN "Asiste" a ON p."nroGrupo" = a."nroGrupo" AND p.dia = a.dia
                    WHERE p."nroGrupo" = $1 AND p.dia = $2
                    GROUP BY p."capacidadMax"
                '''
                capacidad = await conn.fetchrow(query_capacidad, horario.nroGrupo, horario.dia)

                if not capacidad:
                    raise NotFoundException("Horario", f"Grupo {horario.nroGrupo} en día {horario.dia}")

                if capacidad['inscritos'] >= capacidad['capacidadMax']:
                    raise BusinessRuleException(f"El grupo {horario.nroGrupo} del día {horario.dia} está completo.")
                
            # Insertar en Asiste
            await conn.execute('''
                INSERT INTO "Asiste" (dni, "nroGrupo", dia)
                VALUES ($1, $2, $3)
            ''', data.dni, horario.nroGrupo, horario.dia)

            # === NUEVA LÓGICA: GENERAR LA PRIMERA CUOTA ===
            hoy = date.today()
            fecha_fin = hoy + timedelta(days=30) # La cuota dura 30 días
            nombre_mes = calendar.month_name[hoy.month].capitalize()

            await conn.execute('''
                INSERT INTO "Cuota" (dni, pagada, monto, "fechaComienzo", "fechaFin", mes, "nombreTrabajo", "nombreSuscripcion")
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', data.dni, False, monto_cuota, hoy, fecha_fin, nombre_mes, data.nombreTrabajo, data.nombreSuscripcion)

            return AlumnoActivateResponse(
                dni=persona['dni'],
                nombre=persona['nombre'],
                apellido=persona['apellido'],
                email=persona['email'],
                message="Alumno activado y primera cuota generada correctamente."
            )

        except (NotFoundException, DuplicateEntryException, BusinessRuleException) as e:
            raise e # Re-lanzar excepciones de negocio para que el handler las capture
        except Exception as e:
            raise DatabaseException("activar alumno", str(e))


async def listar_alumnos_detalle(conn: Connection) -> List[AlumnoListado]:
    """
    Servicio para listar todos los alumnos con detalles específicos para administradores.
    Combina información de las tablas Persona, Alumno, AlumnoActivo, Cuota y Asiste.
    """
    try:
        query = """
        SELECT
            p.dni,
            p.nombre,
            p.apellido,
            (CASE WHEN aa.dni IS NOT NULL THEN TRUE ELSE FALSE END) as activo,
            (
                SELECT COUNT(*)
                FROM "Cuota" c
                WHERE c.dni = a.dni AND c.pagada = FALSE
            ) as "cuotasPendientes",
            COALESCE(
                (
                    SELECT
                        CASE
                            WHEN LEFT(MIN(asis."nroGrupo"), 1) IN ('1', '2') THEN 'Mañana'
                            WHEN LEFT(MIN(asis."nroGrupo"), 1) IN ('3', '4', '5') THEN 'Tarde'
                            ELSE 'No asignado'
                        END
                    FROM "Asiste" asis
                    WHERE asis.dni = a.dni
                ),
                'No asignado'
            ) as turno
        FROM "Alumno" a
        JOIN "Persona" p ON a.dni = p.dni
        LEFT JOIN "AlumnoActivo" aa ON a.dni = aa.dni
        ORDER BY p.apellido, p.nombre;
        """
        
        resultados = await conn.fetch(query)
        
        # Mapea los resultados al esquema Pydantic
        return [AlumnoListado(**dict(row)) for row in resultados]

    except Exception as e:
        raise DatabaseException("listar alumnos", str(e))


async def obtener_detalle_alumno(conn: Connection, dni: str) -> AlumnoDetalle:
    """
    Servicio para obtener la vista detallada de un único alumno por su DNI.
    """
    try:
        query = """
        SELECT
            p.dni,
            p.nombre,
            p.apellido,
            p.sexo,
            p.email,
            p.telefono,
            (CASE WHEN aa.dni IS NOT NULL THEN TRUE ELSE FALSE END) as activo,
            (
                SELECT COUNT(*)
                FROM "Cuota" c
                WHERE c.dni = a.dni AND c.pagada = FALSE
            ) as "cuotasPendientes",
            COALESCE(
                (
                    SELECT
                        CASE
                            WHEN LEFT(MIN(asis."nroGrupo"), 1) IN ('1', '2') THEN 'Mañana'
                            WHEN LEFT(MIN(asis."nroGrupo"), 1) IN ('3', '4', '5') THEN 'Tarde'
                            ELSE 'No asignado'
                        END
                    FROM "Asiste" asis
                    WHERE asis.dni = a.dni
                ),
                'No asignado'
            ) as turno,
            a."nombreSuscripcion" as suscripcion,
            a."nombreTrabajo" as trabajoactual,
            d."nomProvincia" as provincia,
            d."nomLocalidad" as localidad,
            d.calle as calle,
            d.numero as nro,
            a.nivel as nivel
        FROM "Alumno" a
        JOIN "Persona" p ON a.dni = p.dni
        LEFT JOIN "AlumnoActivo" aa ON a.dni = aa.dni
        LEFT JOIN "Direccion" d ON a.dni = d.dni
        WHERE a.dni = $1;
        """
        
        result = await conn.fetchrow(query, dni)
        
        if not result:
            raise NotFoundException("Alumno", dni)
            
        return AlumnoDetalle(**dict(result))

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("obtener detalle de alumno", str(e))

# === SERVICIO MODIFICADO PARA OBTENER HORARIOS DE UN ALUMNO ===
async def obtener_horarios_alumno(conn: Connection, dni: str) -> List[HorarioAlumno]:
    """
    Servicio para obtener los días y rangos horarios a los que asiste un alumno.
    """
    try:
        # Verificamos que el alumno exista
        alumno_existe = await conn.fetchval('SELECT 1 FROM "Alumno" WHERE dni = $1', dni)
        if not alumno_existe:
            raise NotFoundException("Alumno", dni)

        # Modificamos la consulta para unir con la tabla Horario
        query = """
        SELECT
            dia,
            "nroGrupo"
        FROM "Asiste"
        WHERE dni = $1
        ORDER BY dia;
        """
        
        resultados_db = await conn.fetch(query, dni)
        
        # Formateamos la respuesta en Python
        # horarios_formateados = []
        # for row in resultados_db:
        #     hora_inicio: time = row["horaInicio"]
        #     hora_fin: time = row["horaFin"]
            
        #     # Creamos el string "HH:MM-HH:MM"
        #     horario_str = f"{hora_inicio.strftime('%H:%M')}-{hora_fin.strftime('%H:%M')}"
            
        #     horarios_formateados.append(
        #         HorarioAlumno(dia=row["dia"], horario=horario_str)
        #     )
            
        # return horarios_formateados
    
        return [HorarioAlumno(**dict(row)) for row in resultados_db]

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("obtener horarios de alumno", str(e))

