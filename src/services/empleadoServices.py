from asyncpg import Connection
from typing import List

from schemas.empleadoSchema import (
    EmpleadoCreate,
    EmpleadoResponse,
    EmpleadoListado,
    EmpleadoDetalle,
    HorarioEmpleadoCreate,
    HorarioEmpleadoResponse
)

from utils.security import get_password_hash

from utils.exceptions import (
    DatabaseException, 
    DuplicateEntryException, 
    NotFoundException,
    BusinessRuleException
)

async def crear_empleado_completo(conn: Connection, data: EmpleadoCreate) -> EmpleadoResponse:
    """
    Crea un empleado completo (Persona + Dirección + Empleado + Asignación de Horarios).
    Genera usuario y contraseña automáticos basados en el DNI.
    """
    async with conn.transaction():
        try:
            # 1. Validaciones Previas (Unicidad)
            persona_existe = await conn.fetchval('SELECT 1 FROM "Persona" WHERE dni = $1 OR email = $2', data.dni, data.email)
            if persona_existe:
                raise DuplicateEntryException("Persona (DNI o Email)", data.dni)

            # 2. Generar Credenciales
            # Usuario = DNI, Contraseña = Hash(DNI)
            usuario = data.dni
            password_hash = get_password_hash(data.dni) 

            # 3. Insertar Persona
            await conn.execute('''
                INSERT INTO "Persona" (dni, nombre, apellido, sexo, telefono, email, usuario, contrasenia, "requiereCambioClave")
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)
            ''', data.dni, data.nombre, data.apellido, data.sexo, data.telefono, 
                data.email, usuario, password_hash)

            # 4. Insertar Dirección (Asegurando Provincia/Localidad)
            # 4.1 Upsert Provincia
            await conn.execute('''
                INSERT INTO "Provincia" ("nomProvincia") VALUES ($1)
                ON CONFLICT ("nomProvincia") DO NOTHING
            ''', data.nomProvincia)
            
            # 4.2 Upsert Localidad
            await conn.execute('''
                INSERT INTO "Localidad" ("nomLocalidad", "nomProvincia") VALUES ($1, $2)
                ON CONFLICT ("nomLocalidad", "nomProvincia") DO NOTHING
            ''', data.nomLocalidad, data.nomProvincia)

            # 4.3 Insertar Dirección
            await conn.execute('''
                INSERT INTO "Direccion" ("nomLocalidad", "nomProvincia", numero, calle, dni)
                VALUES ($1, $2, $3, $4, $5)
            ''', data.nomLocalidad, data.nomProvincia, data.numero, data.calle, data.dni)

            # 5. Insertar Empleado
            await conn.execute('''
                INSERT INTO "Empleado" (dni, rol)
                VALUES ($1, $2)
            ''', data.dni, data.rol)

            # 6. Asignar Horarios (Actualizar tabla Pertenece)
            for horario in data.horarios:
                # Verificamos que el grupo exista
                grupo_existe = await conn.fetchval(
                    'SELECT 1 FROM "Pertenece" WHERE "nroGrupo" = $1 AND dia = $2',
                    horario.nroGrupo, horario.dia
                )
                
                if not grupo_existe:
                    # Opcional: Podrías decidir ignorarlo o fallar. Aquí fallamos por seguridad.
                    raise NotFoundException("Grupo/Día", f"{horario.nroGrupo} - {horario.dia}")

                # Asignamos el empleado al grupo
                await conn.execute('''
                    UPDATE "Pertenece"
                    SET "dniEmpleado" = $1
                    WHERE "nroGrupo" = $2 AND dia = $3
                ''', data.dni, horario.nroGrupo, horario.dia)

            return EmpleadoResponse(
                dni=data.dni,
                nombre=data.nombre,
                apellido=data.apellido,
                email=data.email,
                rol=data.rol,
                message="Empleado creado y asignado exitosamente."
            )

        except (DuplicateEntryException, NotFoundException) as e:
            raise e
        except Exception as e:
            raise DatabaseException("crear empleado", str(e))

async def listar_empleados(conn: Connection) -> List[EmpleadoListado]:
    """
    Obtiene la lista de todos los empleados con sus datos personales básicos.
    """
    try:
        query = """
        SELECT 
            p.dni,
            p.nombre,
            p.apellido,
            e.rol
        FROM "Empleado" e
        JOIN "Persona" p ON e.dni = p.dni
        ORDER BY p.apellido, p.nombre
        """
        resultados = await conn.fetch(query)
        return [EmpleadoListado(**dict(row)) for row in resultados]
        
    except Exception as e:
        raise DatabaseException("listar empleados", str(e))

async def obtener_detalle_empleado(conn: Connection, dni: str) -> EmpleadoDetalle:
    """
    Obtiene toda la información de un empleado (Personal, Dirección, Rol y Horarios).
    """
    try:
        # 1. Obtener datos personales, dirección y rol
        query_datos = """
        SELECT 
            p.dni, p.nombre, p.apellido, p.sexo, p.email, p.telefono,
            d."nomProvincia" as provincia, d."nomLocalidad" as localidad, d.calle, d.numero as nro,
            e.rol
        FROM "Empleado" e
        JOIN "Persona" p ON e.dni = p.dni
        LEFT JOIN "Direccion" d ON e.dni = d.dni
        WHERE e.dni = $1
        """
        empleado_data = await conn.fetchrow(query_datos, dni)
        
        if not empleado_data:
            raise NotFoundException("Empleado", dni)

        # 2. Obtener los horarios asignados (Tabla Pertenece)
        query_horarios = """
        SELECT dia, "nroGrupo"
        FROM "Pertenece"
        WHERE "dniEmpleado" = $1
        ORDER BY 
            CASE dia
                WHEN 'Lunes' THEN 1
                WHEN 'Martes' THEN 2
                WHEN 'Miércoles' THEN 3
                WHEN 'Jueves' THEN 4
                WHEN 'Viernes' THEN 5
                WHEN 'Sábado' THEN 6
                WHEN 'Domingo' THEN 7
            END
        """
        horarios_data = await conn.fetch(query_horarios, dni)
        
        # 3. Construir el objeto de respuesta
        # Convertimos los registros de la BD a una lista de diccionarios/objetos
        lista_horarios = [HorarioEmpleadoResponse(**dict(h)) for h in horarios_data]
        
        # Creamos el diccionario final combinando todo
        datos_finales = dict(empleado_data)
        datos_finales['horarios'] = lista_horarios
        
        return EmpleadoDetalle(**datos_finales)

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("obtener detalle del empleado", str(e))

