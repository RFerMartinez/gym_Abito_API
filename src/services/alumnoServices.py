
from asyncpg import Connection
from schemas.alumnoSchema import AlumnoActivate, AlumnoActivateResponse
from utils.exceptions import NotFoundException, DuplicateEntryException, BusinessRuleException, DatabaseException

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
            
            suscripcion = await conn.fetchval('SELECT 1 FROM "Suscripcion" WHERE "nombreSuscripcion" = $1', data.nombreSuscripcion)
            if not suscripcion:
                raise NotFoundException("Suscripción", data.nombreSuscripcion)

            # 4. Insertar en Alumno
            await conn.execute('''
                INSERT INTO "Alumno" (dni, sexo, "nombreTrabajo", "nombreSuscripcion", nivel, deporte)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', data.dni, data.sexo, data.nombreTrabajo, data.nombreSuscripcion, data.nivel, data.deporte)

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

            return AlumnoActivateResponse(
                dni=persona['dni'],
                nombre=persona['nombre'],
                apellido=persona['apellido'],
                email=persona['email'],
                message="Alumno activado correctamente."
            )

        except (NotFoundException, DuplicateEntryException, BusinessRuleException) as e:
            raise e # Re-lanzar excepciones de negocio para que el handler las capture
        except Exception as e:
            raise DatabaseException("activar alumno", str(e))