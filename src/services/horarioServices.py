import json
from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional
from schemas.horarioSchema import (
    HorarioCreate, HorarioResponse, PerteneceCreate,
    HorarioCompletoResponse, GrupoConDetalles, DiaConCapacidad
)
from utils.exceptions import NotFoundException, DatabaseException, DuplicateEntryException

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