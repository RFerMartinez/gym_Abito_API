# constants.py
APP_NAME = "gym_manager_api"
TITLE = "Gym Manager API"
DESCRIPTION = """
Bienvenido a la documentación de la API de Gestión de Gimnasio!

Esta API proporciona endpoints para gestionar alumnos, empleados, suscripciones, asistencias, pagos y actividades en un sistema de gimnasio. Los principales módulos incluyen:

## Módulos Principales

### Gestión de Alumnos
- Registrar nuevos alumnos (activos/inactivos)
- Actualizar información personal
- Gestionar suscripciones (planes semanales o pago por día)
- Ver historial de asistencia y pagos

### Gestión de Empleados
- Registrar empleados y asignar horarios
- Gestionar grupos y actividades asignadas
- Control de acceso al sistema

### Asistencias y Grupos
- Registrar asistencia diaria con fecha/hora exacta
- Gestionar grupos con límite de capacidad
- Asignar franjas horarias fijas por grupo

### Gestión de Pagos
- Generación automática de cuotas mensuales para alumnos activos
- Registro de pagos (incluyendo pagos adelantados)
- Identificación de morosos

### Planes de Entrenamiento
- Crear planes personalizados por alumno
- Gestionar ejercicios con series y repeticiones
- Asignar actividades según objetivos (musculación, rehabilitación, etc.)

### Sistema de Reclamos
- Registro de reclamos/sugerencias de alumnos
- Seguimiento de resolución

## Autenticación
La API utiliza autenticación JWT para proteger los endpoints. Los empleados deben iniciar sesión para acceder a las funcionalidades.

## Modelo de Negocio
El sistema soporta dos tipos de alumnos:
- **Alumnos activos**: Con suscripción semanal (1-6 días/semana) y cuota mensual automática
- **Alumnos inactivos**: Pago por día sin suscripción

Se gestionan 6 tipos de actividades con distintos niveles:
1. Musculación
2. Mantenimiento físico
3. Aeróbico/definición
4. Funcional
5. Preparación física para deportes
6. Rehabilitación

## Códigos de Error
- **200 OK**: Solicitud exitosa
- **201 Created**: Recurso creado
- **400 Bad Request**: Datos inválidos
- **401 Unauthorized**: Autenticación requerida
- **403 Forbidden**: Permisos insuficientes
- **404 Not Found**: Recurso no existe
- **422 Unprocessable Entity**: Error de validación
- **500 Internal Server Error**: Error del servidor
"""

CONTACT = {
    "name": "Tu Nombre",
    "url": "https://tudominio.com/contacto",
    "email": "contacto@tudominio.com"
}

LICENSE_INFO = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

# Configuración de Swagger
# SWAGGER_UI_PARAMETERS = {
#     "syntaxHighlight.theme": "obsidian",
#     "docExpansion": "none"
# }

# SWAGGER_FAVICON_URL = "/static/favicon.ico"

# # Constantes de negocio
# ACTIVITY_TYPES = [
#     "Musculación",
#     "Mantenimiento físico",
#     "Aeróbico/definición",
#     "Funcional",
#     "Preparación física para deportes",
#     "Rehabilitación"
# ]

# SUBSCRIPTION_TYPES = {
#     "1_day": "1 día/semana",
#     "2_days": "2 días/semana",
#     "3_days": "3 días/semana",
#     "4_days": "4 días/semana",
#     "5_days": "5 días/semana",
#     "6_days": "6 días/semana",
#     "pay_per_day": "Pago por día"
# }

# MEMBERSHIP_STATUS = [
#     "active",
#     "inactive"
# ]

# # Configuración de grupos
# MAX_GROUP_CAPACITY = 15  # Máximo de alumnos por grupo
# GROUP_TIME_SLOTS = [
#     "07:00-09:00",
#     "09:00-11:00",
#     "11:00-13:00",
#     "15:00-17:00",
#     "17:00-19:00",
#     "19:00-21:00"
# ]