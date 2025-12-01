from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from asyncpg import Connection
from typing import Annotated, Optional
from datetime import timedelta

from fastapi.security import OAuth2PasswordRequestForm

from core.session import get_db
from schemas.authSchema import (
    RegistroPaso1, 
    RegistroPaso2, 
    LoginRequest, 
    Token, 
    UserResponse,
    EmailVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirm
)
from services.authServices import (
    iniciar_registro_paso1,
    completar_registro_paso2,
    authenticate_user,
    verify_email_token,
    es_alumno,
    es_empleado
)
from utils.security import (
    create_access_token,
    create_refresh_token,
    verify_registration_token
)
from api.dependencies.auth import get_current_user
from utils.exceptions import DuplicateEntryException, DatabaseException

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_409_CONFLICT: {"description": "Conflicto - El recurso ya existe"}
    }
)

# Almacenamiento temporal para datos del paso 1
# temp_registry = {}

@router.post("/registro-paso1", status_code=status.HTTP_200_OK)
async def registro_paso1(
    user_data: RegistroPaso1, 
    db: Connection = Depends(get_db)
):
    """
    Primer paso del registro: valida email, usuario y envía correo de verificación.
    """
    try:
        token = await iniciar_registro_paso1(db, user_data)
        
        # Almacenar temporalmente los datos del paso 1
        # temp_registry[token] = {
        #     "email": user_data.email,
        #     "usuario": user_data.usuario,
        #     "contrasenia": user_data.contrasenia
        # }
        
        return {"message": "Correo de verificación enviado", "token": token}
    except DuplicateEntryException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el registro: {str(e)}"
        )

@router.post("/registro-paso2", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def registro_paso2(
    user_data: RegistroPaso2,
    token: str,
    db: Connection = Depends(get_db)
):
    """
    Segundo paso del registro: completa información personal después de verificar email.
    """
    # Verificar y decodificar el token JWT
    paso1_data = verify_registration_token(token)

    if not paso1_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o expirado"
        )
    
    # Obtener datos del token decodificado
    email = paso1_data["email"]
    usuario = paso1_data["usuario"]
    contrasenia = paso1_data["contrasenia"]

    try:
        # Completar registro
        user = await completar_registro_paso2(db, user_data, email, usuario, contrasenia)
        
        # Eliminar datos temporales
        #del temp_registry[token]
        
        return user
    except DuplicateEntryException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completando registro: {str(e)}"
        )

@router.get("/verify-email")
async def verify_email(
    token: str,
    db: Connection = Depends(get_db)
):
    """
    Verifica un email usando el token enviado por correo.
    """
    email = await verify_email_token(db, token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o expirado"
        )
    
    return {"message": "Email verificado correctamente", "email": email}

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Connection = Depends(get_db)
):
    """
    Inicia sesión y devuelve tokens de acceso y refresh.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["usuario"]}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user["usuario"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Connection = Depends(get_db) # <--- 2. INYECTAR LA CONEXIÓN A LA BD
):
    """
    Obtiene información del usuario actualmente autenticado y sus roles.
    """
    dni = current_user["dni"]
    
    # 3. VERIFICAR ROLES EN LA BASE DE DATOS
    is_alumno = await es_alumno(db, dni)
    is_empleado = await es_empleado(db, dni)
    is_admin = current_user["esAdmin"] # Este dato ya viene en la tabla Persona
    
    # 4. DETERMINAR SI ES "SOLO PERSONA" (Ningún rol asignado)
    is_persona = not (is_alumno or is_empleado or is_admin)
    
    # 5. AGREGAR DATOS A LA RESPUESTA
    # Actualizamos el diccionario del usuario con los nuevos campos calculados
    current_user.update({
        "esAlumno": is_alumno,
        "esEmpleado": is_empleado,
        "esPersona": is_persona
    })
    
    return current_user