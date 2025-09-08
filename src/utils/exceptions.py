from fastapi import HTTPException, status
from typing import Optional, Any

class AppException(HTTPException):
    """Clase base para todas las excepciones personalizadas de la aplicación"""
    
    def __init__(
        self, 
        detail: str, 
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[dict] = None
    ):
        super().__init__(
            status_code=status_code, 
            detail=detail, 
            headers=headers
        )

class NotFoundException(AppException):
    """Excepción para recursos no encontrados"""
    
    def __init__(self, resource: str, identifier: Optional[Any] = None):
        detail = f"{resource} no encontrado"
        if identifier is not None:
            detail += f" con identificador: {identifier}"
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_404_NOT_FOUND
        )

class DuplicateEntryException(AppException):
    """Excepción para entradas duplicadas"""
    
    def __init__(self, field: str, value: Any):
        detail = f"Ya existe un registro con {field} = '{value}'"
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_409_CONFLICT
        )

class DatabaseException(AppException):
    """Excepción para errores de base de datos"""
    
    def __init__(self, operation: str, error: str):
        detail = f"Error en la operación '{operation}': {error}"
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ValidationException(AppException):
    """Excepción para errores de validación"""
    
    def __init__(self, field: str, message: str):
        detail = f"Error de validación en {field}: {message}"
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class AuthenticationException(AppException):
    """Excepción para errores de autenticación"""
    
    def __init__(self, detail: str = "Credenciales inválidas"):
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationException(AppException):
    """Excepción para errores de autorización"""
    
    def __init__(self, detail: str = "No tiene permisos para realizar esta acción"):
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_403_FORBIDDEN
        )

class BusinessRuleException(AppException):
    """Excepción para violaciones de reglas de negocio"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=detail, 
            status_code=status.HTTP_400_BAD_REQUEST
        )