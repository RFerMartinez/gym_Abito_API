from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime

# Esquema para el Paso 1 del registro
class RegistroPaso1(BaseModel):
    email: EmailStr = Field(..., max_length=60 ,description="Email del usuario")
    usuario: str = Field(..., min_length=3, max_length=30, description="Nombre de usuario")
    contrasenia: str = Field(..., min_length=6, description="Contraseña")
    confirmar_contrasenia: str = Field(..., description="Confirmación de contraseña")

    @field_validator('usuario')
    @classmethod
    def validar_usuario(cls, v: str) -> str:
        if ' ' in v:
            raise ValueError('El usuario no puede contener espacios')
        if not v.isalnum():
            raise ValueError('El usuario solo puede contener letras y números')
        return v

    @field_validator('confirmar_contrasenia')
    @classmethod
    def contrasenias_coinciden(cls, v: str, values) -> str:
        if 'contrasenia' in values.data and v != values.data['contrasenia']:
            raise ValueError('Las contraseñas no coinciden')
        return v

# Esquema para el Paso 2 del registro
class RegistroPaso2(BaseModel):
    dni: str = Field(..., min_length=8, max_length=8, pattern="^[0-9]+$", description="DNI sin puntos")
    nombre: str = Field(..., max_length=40, description="Nombre")
    apellido: str = Field(..., max_length=40, description="Apellido")
    telefono: str = Field(..., max_length=15, description="Teléfono")
    
    # --- CAMBIO: Agregamos el campo sexo ---
    sexo: str = Field(..., max_length=1, description="Sexo ('M' o 'F')")
    
    nomProvincia: str = Field(..., max_length=40, description="Nombre de la provincia")
    nomLocalidad: str = Field(..., max_length=40, description="Nombre de la localidad")
    calle: str = Field(..., max_length=60, description="Calle")
    numero: str = Field(default="S/N", max_length=5, description="Número de calle")

    @field_validator('numero')
    @classmethod
    def validar_numero(cls, v: str) -> str:
        if v != "S/N" and not v.isdigit():
            raise ValueError("El número debe ser 'S/N' o un valor numérico")
        return v

    # --- CAMBIO: Agregamos validador para sexo ---
    @field_validator('sexo')
    @classmethod
    def validar_sexo(cls, v: str) -> str:
        sexo_upper = v.upper()
        if sexo_upper not in ['M', 'F']:
            raise ValueError("El sexo debe ser 'M' o 'F'")
        return sexo_upper

# Esquema para login
class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario o email")
    password: str = Field(..., description="Contraseña")

# Esquema para tokens
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None

# Esquema para respuesta de usuario
class UserResponse(BaseModel):
    dni: str
    nombre: str
    apellido: str
    telefono: str
    email: str
    usuario: str
    requiereCambioClave: bool
    esAdmin: bool = Field(False, description="Indica si es administrador")
    
    # --- NUEVOS CAMPOS ---
    esAlumno: bool = Field(False, description="Indica si la persona es un alumno")
    esEmpleado: bool = Field(False, description="Indica si la persona es un empleado")
    esPersona: bool = Field(False, description="TRUE si no es ni admin, ni alumno, ni empleado")
    
    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    requiere_cambio_contrasenia: bool
    user: UserResponse

# Esquema para verificación de email
class EmailVerificationRequest(BaseModel):
    token: str

# Esquema para solicitud de reseteo de contraseña
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, description="La nueva contraseña del usuario")

