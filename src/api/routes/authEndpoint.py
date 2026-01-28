from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from asyncpg import Connection
from typing import Annotated, Optional
from datetime import timedelta

from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt

from core.session import get_db

from schemas.authSchema import (
    RegistroPaso1, 
    RegistroPaso2, 
    LoginRequest, 
    Token, 
    UserResponse,
    EmailVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest
)

from services.authServices import (
    ejecutar_recuperacion_contrasenia,
    iniciar_registro_paso1,
    completar_registro_paso2,
    authenticate_user,
    solicitar_recuperacion_contrasenia,
    verify_email_token,
    es_alumno,
    es_empleado,
    cambiar_contrasenia_primer_ingreso
)

from core.config import settings
from utils.simpleQueries import get_user_by_username
from utils.security import (
    create_access_token,
    create_refresh_token,
    verify_registration_token,
    
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
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
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

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: PasswordResetRequest,
    db: Connection = Depends(get_db)
):
    """
    Paso 1: Recibe el email y envía el correo con el enlace de recuperación.
    """
    await solicitar_recuperacion_contrasenia(conn=db, email=request.email)
    return {"message": "Si el correo existe, se ha enviado un enlace de recuperación."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    data: PasswordResetConfirm,
    db: Connection = Depends(get_db)
):
    """
    Paso 2: Recibe el token y la nueva contraseña para actualizarla.
    """
    await ejecutar_recuperacion_contrasenia(conn=db, data=data)
    return {"message": "Contraseña actualizada correctamente."}

@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Cambiar contraseña (Usuario Logueado)",
    description="Permite cambiar la contraseña actual y desactiva la obligación de cambio de clave."
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user), # <--- Requiere estar logueado
    db: Connection = Depends(get_db)
):
    dni = current_user['dni']
    await cambiar_contrasenia_primer_ingreso(conn=db, dni=dni, new_password=request.new_password)
    return {"message": "Contraseña actualizada correctamente. Sesión asegurada."}

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str, 
    db: Connection = Depends(get_db)
):
    """
    Genera un nuevo access_token usando un refresh_token válido.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Validar el refresh token (usando la misma lógica que get_current_user pero solo validación)
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verificar que el usuario siga existiendo en BD (Opcional pero recomendado)
    user = await get_user_by_username(db, username)
    if not user:
        raise credentials_exception

    # Crear nuevo access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, 
        expires_delta=access_token_expires
    )
    
    # Podrías rotar el refresh token aquí también si quisieras mayor seguridad, 
    # pero para simplificar devolvemos solo el access_token nuevo y el mismo refresh (o uno nuevo)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token # Devolvemos el mismo para mantenerlo vivo
    }