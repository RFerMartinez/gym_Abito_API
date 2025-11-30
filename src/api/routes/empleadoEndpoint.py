from typing import List
from fastapi import APIRouter, Depends, status
from asyncpg import Connection

from core.session import get_db

from api.dependencies.security import admin_required

from schemas.empleadoSchema import (
    EmpleadoCreate,
    EmpleadoResponse,
    EmpleadoListado,
    EmpleadoDetalle
)

from services import (
    empleadoServices
)

router = APIRouter(
    prefix="/empleados",
    tags=["Empleados"]
)

@router.post(
    "/",
    response_model=EmpleadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo empleado (Admin)",
    description="Crea persona, dirección, empleado y asigna horarios. Usuario y pass por defecto es el DNI.",
    dependencies=[Depends(admin_required)] # <-- Solo Admin
)
async def crear_nuevo_empleado(
    empleado_data: EmpleadoCreate,
    db: Connection = Depends(get_db)
):
    return await empleadoServices.crear_empleado_completo(conn=db, data=empleado_data)

@router.get(
    "/",
    response_model=List[EmpleadoListado],
    summary="Listar todos los empleados (Admin)",
    description="Obtiene una lista de empleados con DNI, Nombre, Apellido y Rol.",
    dependencies=[Depends(admin_required)] # <-- Solo Admin
)
async def obtener_lista_empleados(
    db: Connection = Depends(get_db)
):
    return await empleadoServices.listar_empleados(conn=db)

@router.get(
    "/{dni}",
    response_model=EmpleadoDetalle,
    summary="Obtener detalle de un empleado (Admin)",
    description="Devuelve datos personales, dirección, rol y lista de horarios asignados.",
    dependencies=[Depends(admin_required)] # Solo Admin puede ver detalles completos de empleados
)
async def get_empleado_detalle(
    dni: str,
    db: Connection = Depends(get_db)
):
    return await empleadoServices.obtener_detalle_empleado(conn=db, dni=dni)

