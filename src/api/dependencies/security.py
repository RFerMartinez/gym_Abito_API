from fastapi import Depends, HTTPException, status
from asyncpg import Connection
from typing import List

from api.dependencies.auth import get_current_user
from services.authServices import (
    es_administrador, 
    es_empleado, 
    es_alumno_activo,
    es_alumno
)
from core.session import get_db

# Dependencia para administradores
async def admin_required(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    if not await es_administrador(db, current_user["dni"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user

# Dependencia para empleados
async def empleado_required(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    if not await es_empleado(db, current_user["dni"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de empleado"
        )
    return current_user

# Dependencia para alumnos activos
async def alumno_activo_required(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    if not await es_alumno_activo(db, current_user["dni"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere ser alumno activo"
        )
    return current_user

# Dependencia para cualquier alumno (activo o inactivo)
async def alumno_required(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    if not await es_alumno(db, current_user["dni"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere ser alumno"
        )
    return current_user

# Dependencia para administradores o empleados
async def staff_required(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    es_admin = await es_administrador(db, current_user["dni"])
    es_emp = await es_empleado(db, current_user["dni"])
    
    if not (es_admin or es_emp):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de staff (admin o empleado)"
        )
    return current_user

async def staff_or_alumno_required(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    """
    Verifica si el usuario es staff (admin o empleado) O si es alumno.
    """
    es_admin = await es_administrador(db, current_user["dni"])
    es_emp = await es_empleado(db, current_user["dni"])
    es_alu = await es_alumno(db, current_user["dni"]) #
    
    if not (es_admin or es_emp or es_alu):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de staff o de alumno para acceder a este recurso."
        )
    return current_user