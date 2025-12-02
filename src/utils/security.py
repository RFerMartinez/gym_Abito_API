import secrets
import string
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Funciones de utilidad para JWT y contraseñas
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)



# ESTA FUNCIÓN ES NUEVA
def create_registration_token(data: dict) -> str:
    """Crea un token JWT de corta duración para el proceso de registro."""
    to_encode = data.copy()
    # El token para registrarse expirará en 15 minutos
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "purpose": "registration"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# ESTA FUNCIÓN ES NUEVA
def verify_registration_token(token: str) -> Optional[dict]:
    """Decodifica y valida el token de registro, devolviendo los datos."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Verificamos que el propósito del token sea el correcto
        if payload.get("purpose") != "registration":
            return None
        return payload
    except JWTError:
        return None


# ==========================================
# FUNCIONES PARA RECUPERACIÓN DE CONTRASEÑA
# ==========================================
def create_password_reset_token(data: dict) -> str:
    """Crea un token JWT específico para restablecer contraseña."""
    to_encode = data.copy()
    # Expiración corta (ej: 15 minutos)
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Forzamos el propósito correcto
    to_encode.update({"exp": expire, "purpose": "password_reset"})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[dict]:
    """Valida que el token sea válido y tenga el propósito de reset."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Validación estricta del propósito
        if payload.get("purpose") != "password_reset":
            return None
            
        return payload
    except JWTError:
        return None



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def generate_verification_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))