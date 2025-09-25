from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from api.dependencies.security import admin_required, staff_required
from api.dependencies.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get("/dashboard")
async def dashboard_admin(
    current_user: dict = Depends(admin_required)
):
    """Solo administradores"""
    return {"message": "Dashboard administrativo", "user": current_user}

@router.get("/reportes")
async def reportes_administrativos(
    current_user: dict = Depends(staff_required)  # Admin o empleados
):
    """Staff (admin o empleados)"""
    return {"message": "Reportes administrativos", "user": current_user}

@router.post("/usuarios/{dni}/activar")
async def activar_usuario(
    dni: str,
    db: Connection = Depends(get_db),
    current_user: dict = Depends(admin_required)
):
    """Solo administradores pueden activar usuarios"""
    # Lógica para activar usuario
    return {"message": f"Usuario {dni} activado"}

@router.get("/mi-perfil")
async def perfil_admin(
    current_user: dict = Depends(get_current_user)  # Cualquier usuario autenticado
):
    """Cualquier usuario autenticado puede ver su perfil"""
    return current_user