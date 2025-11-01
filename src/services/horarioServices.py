import json
from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional
from datetime import time

from schemas.horarioSchema import (
    HorarioCreate,
    HorarioResponse,
    PerteneceCreate,
    HorarioCompletoResponse,
    GrupoConDetalles,
    DiaConCapacidad,
    HorarioCompletoCreate,
    PerteneceResponse
)

from utils.exceptions import (
    BusinessRuleException,
    NotFoundException,
    DatabaseException,
    DuplicateEntryException
)

async def crear_horario(conn: Connection, horario: HorarioCreate) -> HorarioResponse:
    """
    Crea un nuevo horario/grupo en el sistema
    """
    try:
        query = """
        INSERT INTO "Horario" ("nroGrupo", "horaInicio", "horaFin")
        VALUES ($1, $2, $3)
        RETURNING "nroGrupo", "horaInicio", "horaFin"
        """
        result = await conn.fetchrow(
            query,
            horario.nroGrupo,
            horario.horaInicio,
            horario.horaFin
        )
        return HorarioResponse(**result)
    
    except UniqueViolationError:
        raise DuplicateEntryException("nroGrupo", horario.nroGrupo)
    except Exception as e:
        raise DatabaseException("crear horario", str(e))

async def crear_relacion_grupo_dia(conn: Connection, pertenece: PerteneceCreate) -> dict:
    """
    Crea o actualiza la relación entre un grupo y un día con validaciones de FK
    """
    try:
        # Verificar que el grupo existe
        grupo_exists = await conn.fetchval(
            'SELECT 1 FROM "Horario" WHERE "nroGrupo" = $1', 
            pertenece.nroGrupo
        )
        if not grupo_exists:
            raise NotFoundException("Grupo", pertenece.nroGrupo)
        
        # Verificar que el día existe
        dia_exists = await conn.fetchval(
            'SELECT 1 FROM "Dia" WHERE dia = $1', 
            pertenece.dia
        )
        if not dia_exists:
            raise NotFoundException("Día", pertenece.dia)
        
        # Verificar que el empleado existe (si se proporciona)
        if pertenece.dniEmpleado:
            empleado_exists = await conn.fetchval(
                'SELECT 1 FROM "Empleado" WHERE dni = $1', 
                pertenece.dniEmpleado
            )
            if not empleado_exists:
                raise NotFoundException("Empleado", pertenece.dniEmpleado)

        query = """
        INSERT INTO "Pertenece" ("nroGrupo", dia, "capacidadMax", "dniEmpleado")
        VALUES ($1, $2, $3, $4)
        ON CONFLICT ("nroGrupo", dia) 
        DO UPDATE SET 
            "capacidadMax" = EXCLUDED."capacidadMax",
            "dniEmpleado" = EXCLUDED."dniEmpleado"
        RETURNING "nroGrupo", dia, "capacidadMax", "dniEmpleado"
        """
        
        result = await conn.fetchrow(
            query,
            pertenece.nroGrupo,
            pertenece.dia,
            pertenece.capacidadMax,
            pertenece.dniEmpleado
        )
        
        return dict(result)

    except ForeignKeyViolationError as e:
        # Esto captura cualquier violación de FK que no hayamos validado manualmente
        raise DatabaseException("crear relación grupo-día", f"Error de integridad referencial: {str(e)}")
    except NotFoundException:
        raise  # Re-lanzamos las excepciones que ya manejamos
    except Exception as e:
        raise DatabaseException("crear relación grupo-día", str(e))

async def obtener_horarios_completos(conn: Connection) -> List[HorarioCompletoResponse]:
    try:
        query = """
        SELECT 
            h."nroGrupo",
            h."horaInicio",
            h."horaFin",
            COALESCE(
                JSON_AGG(
                    JSON_BUILD_OBJECT(
                        'dia', p.dia,
                        'capacidadMax', p."capacidadMax",
                        'empleado', p."dniEmpleado",
                        'alumnos_inscritos', (
                            SELECT COUNT(*) 
                            FROM "Asiste" a 
                            WHERE a."nroGrupo" = h."nroGrupo" 
                            AND a.dia = p.dia
                        )
                    )
                ) FILTER (WHERE p.dia IS NOT NULL),
                '[]'::json
            ) as dias_info
        FROM "Horario" h
        LEFT JOIN "Pertenece" p ON h."nroGrupo" = p."nroGrupo"
        GROUP BY h."nroGrupo", h."horaInicio", h."horaFin"
        ORDER BY h."horaInicio"
        """
        resultados = await conn.fetch(query)
        
        horarios = []
        for row in resultados:
            # Convertir la cadena JSON a lista de Python
            dias_info = json.loads(row["dias_info"]) if isinstance(row["dias_info"], str) else row["dias_info"]

            horario_data = {
                "nroGrupo": row["nroGrupo"],
                "horaInicio": row["horaInicio"],
                "horaFin": row["horaFin"],
                "dias_asignados": dias_info  # Ahora es una lista, no una cadena
            }
            horarios.append(HorarioCompletoResponse(**horario_data))
        return horarios

    except Exception as e:
        raise DatabaseException("obtener horarios completos", str(e))

async def obtener_horarios_por_dia_service(conn: Connection, dia: str) -> List[GrupoConDetalles]:
    # Obtener todos los grupos/horarios para un día específico
    try:
        # Verificar que el día existe
        dia_exists = await conn.fetchval(
            'SELECT 1 FROM "Dia" WHERE dia = $1', 
            dia
        )
        if not dia_exists:
            raise NotFoundException("Día", dia)

        query = """
        SELECT 
            h."nroGrupo",
            h."horaInicio",
            h."horaFin",
            p."capacidadMax",
            p."dniEmpleado",
            (
                SELECT COUNT(*) 
                FROM "Asiste" a 
                WHERE a."nroGrupo" = h."nroGrupo" 
                AND a.dia = p.dia
            ) as alumnos_inscritos
        FROM "Horario" h
        JOIN "Pertenece" p ON h."nroGrupo" = p."nroGrupo"
        WHERE p.dia = $1
        ORDER BY h."horaInicio"
        """
        
        resultados = await conn.fetch(query, dia)
        
        grupos = []
        for row in resultados:
            grupo_data = {
                "nroGrupo": row["nroGrupo"],
                "horario": {
                    "nroGrupo": row["nroGrupo"],
                    "horaInicio": row["horaInicio"],
                    "horaFin": row["horaFin"]
                },
                "dias": [{
                    "dia": dia,
                    "capacidadMax": row["capacidadMax"],
                    "empleado": row["dniEmpleado"],
                    "alumnos_inscritos": row["alumnos_inscritos"] or 0
                }]
            }
            grupos.append(GrupoConDetalles(**grupo_data))
        
        return grupos

    except Exception as e:
        raise DatabaseException("obtener horarios por día", str(e))

async def actualizar_capacidad_grupo(
    conn: Connection, 
    nroGrupo: str, 
    dia: str, 
    capacidad: int
) -> dict:
    """
    Actualiza la capacidad máxima para un grupo en un día específico
    """
    try:
        query = """
        UPDATE "Pertenece" 
        SET "capacidadMax" = $1
        WHERE "nroGrupo" = $2 AND dia = $3
        RETURNING "nroGrupo", dia, "capacidadMax"
        """
        
        result = await conn.fetchrow(query, capacidad, nroGrupo, dia)
        
        if not result:
            raise NotFoundException("Relación grupo-día", f"{nroGrupo}-{dia}")
        
        return dict(result)

    except Exception as e:
        raise DatabaseException("actualizar capacidad grupo", str(e))

async def eliminar_relacion_grupo_dia(conn: Connection, nroGrupo: str, dia: str) -> bool:
    """
    Elimina la relación entre un grupo y un día
    """
    try:
        result = await conn.execute(
            'DELETE FROM "Pertenece" WHERE "nroGrupo" = $1 AND dia = $2',
            nroGrupo, dia
        )
        
        if result == "DELETE 0":
            raise NotFoundException("Relación grupo-día", f"{nroGrupo}-{dia}")
        
        return True

    except NotFoundException:
        raise
    except Exception as e:
        raise DatabaseException("eliminar relación grupo-día", str(e))

async def check_horario_overlap(
    conn: Connection, 
    hora_inicio: time, 
    hora_fin: time, 
    nro_grupo_excluir: Optional[str] = None
) -> bool:
    """
    Verifica si un nuevo rango horario (NewStart, NewEnd) se superpone 
    con alguno existente (OldStart, OldEnd).

    La lógica de superposición es: NewStart < OldEnd AND NewEnd > OldStart
    """
    try:
        # $1 = NewStart (hora_inicio)
        # $2 = NewEnd (hora_fin)
        # "horaFin" = OldEnd
        # "horaInicio" = OldStart
        query = """
        SELECT 1 FROM "Horario"
        WHERE $1 < "horaFin" AND $2 > "horaInicio"
        """
        params = [hora_inicio, hora_fin]

        # Si estamos editando, excluimos el grupo actual de la comprobación
        if nro_grupo_excluir:
            query += ' AND "nroGrupo" != $3'
            params.append(nro_grupo_excluir)
        
        # fetchval retornará 1 si encuentra un overlap, o None si no
        overlap = await conn.fetchval(query, *params)
        
        # Si overlap no es None, significa que encontró un registro (overlap=True)
        return overlap is not None
    
    except Exception as e:
        # Si falla la consulta, por precaución no dejamos crear
        print(f"Error crítico chequeando superposición horaria: {e}")
        # Devolvemos True para "fallar en modo seguro" (prevenir la creación)
        return True

# --- NUEVO SERVICIO TRANSACCIONAL ---
async def crear_horario_completo(
    conn: Connection, 
    horario_data: HorarioCompletoCreate
) -> HorarioCompletoResponse:
    """
    De forma transaccional, crea el Horario (grupo) y asigna sus días (Pertenece).
    Valida la superposición de horarios.
    """
    
    # 1. Validación de "consideración": Chequear superposición horaria
    if await check_horario_overlap(conn, horario_data.horaInicio, horario_data.horaFin):
        raise BusinessRuleException(f"El rango horario {horario_data.horaInicio.strftime('%H:%M')}-{horario_data.horaFin.strftime('%H:%M')} se superpone con un grupo existente.")

    async with conn.transaction():
        try:
            # 2. Crear el Horario (Grupo) principal
            # Reutilizamos el servicio que ya tenías
            horario_creado = await crear_horario(conn, HorarioCreate(
                nroGrupo=horario_data.nroGrupo,
                horaInicio=horario_data.horaInicio,
                horaFin=horario_data.horaFin
            ))
            
            dias_asignados_response = []
            
            # 3. Asignar cada día de la lista
            for dia_data in horario_data.dias_asignados:
                # Preparamos el payload para el servicio existente
                pertenece_data = PerteneceCreate(
                    nroGrupo=horario_creado.nroGrupo,
                    dia=dia_data.dia,
                    capacidadMax=dia_data.capacidadMax,
                    dniEmpleado=dia_data.dniEmpleado
                )
                
                # Reutilizamos el servicio de asignación que ya valida FKs (Día, Empleado)
                dia_asignado_dict = await crear_relacion_grupo_dia(conn, pertenece_data)
                
                # Preparamos la sub-respuesta
                dias_asignados_response.append(DiaConCapacidad(
                    dia=dia_asignado_dict['dia'],
                    capacidadMax=dia_asignado_dict['capacidadMax'],
                    empleado=dia_asignado_dict['dniEmpleado'],
                    alumnos_inscritos=0 # Siempre es 0 al crear
                ))
        
            # 4. Si todo salió bien, devolver la respuesta completa
            return HorarioCompletoResponse(
                nroGrupo=horario_creado.nroGrupo,
                horaInicio=horario_creado.horaInicio,
                horaFin=horario_creado.horaFin,
                dias_asignados=dias_asignados_response
            )

        except (DuplicateEntryException, NotFoundException, BusinessRuleException) as e:
            raise e # Re-lanzar excepciones de negocio para el handler
        except ForeignKeyViolationError as e:
            # Error si un día o DNI de empleado no existe
            raise NotFoundException("Día o Empleado", f"Verifique que los días y DNI de empleados sean correctos: {e}")
        except Exception as e:
            raise DatabaseException("crear horario completo", str(e))

async def eliminar_horario_completo(conn: Connection, nroGrupo: str) -> None:
    """
    Elimina un grupo (Horario) y todas sus asignaciones (Pertenece)
    de forma transaccional, solo si no tiene alumnos inscritos.
    """
    async with conn.transaction():
        try:
            # 1. Verificar que no haya alumnos inscritos (Tu verificación)
            alumnos_inscritos = await conn.fetchval(
                'SELECT 1 FROM "Asiste" WHERE "nroGrupo" = $1 LIMIT 1',
                nroGrupo
            )
            
            if alumnos_inscritos:
                raise BusinessRuleException(f"El grupo {nroGrupo} tiene alumnos inscritos. Primero debe reasignarlos para poder eliminar el grupo.")

            # 2. Eliminar las relaciones en "Pertenece" (Tu lógica)
            # (Esto se ejecuta primero por la FK)
            await conn.execute(
                'DELETE FROM "Pertenece" WHERE "nroGrupo" = $1',
                nroGrupo
            )
            
            # 3. Eliminar el grupo en "Horario" (Tu lógica)
            result = await conn.execute(
                'DELETE FROM "Horario" WHERE "nroGrupo" = $1',
                nroGrupo
            )
            
            # 4. Verificar si el grupo realmente existía
            if result == "DELETE 0":
                # Si "Horario" no borró nada, es que el grupo no existía.
                raise NotFoundException("Grupo", nroGrupo)
        
        except (BusinessRuleException, NotFoundException) as e:
            raise e # Re-lanzar para el handler de FastAPI
        except ForeignKeyViolationError:
            # Esto es un seguro, pero la comprobación de "Asiste" debería atajarlo.
            raise BusinessRuleException(f"El grupo {nroGrupo} tiene dependencias (posiblemente alumnos) y no se puede eliminar.")
        except Exception as e:
            raise DatabaseException("eliminar horario", str(e))

