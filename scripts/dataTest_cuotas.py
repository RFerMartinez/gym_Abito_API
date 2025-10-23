import csv
import random
from datetime import datetime, timedelta

def generar_cuotas_csv(nombre_archivo="Cuota.csv", cantidad_registros=1000):
    """
    Genera un archivo CSV con registros de cuotas de gimnasio.

    Args:
        nombre_archivo (str): El nombre del archivo CSV a crear.
        cantidad_registros (int): El número de registros a generar.
    """
    headers = [
        "idCuota", "dni", "pagada", "monto", "fechaComienzo", "fechaFin",
        "mes", "nombreTrabajo", "nombreSuscripcion"
    ]

    # Datos de ejemplo para dar variedad
    dnis_ejemplo = [
        "42276404",
        # "38123456",
        # "40987654",
        # "35555666",
        # "41789123"
    ]
    trabajos_ejemplo = [
        "Preparación Física",
        "Musculación",
        "Mantenimiento",
        # "Funcional",
        # "Rehabilitación"
    ]
    suscripciones_ejemplo = [
        "3 días a la semana",
        "5 días a la semana",
        # "Pase libre"
    ]

    # Fecha de inicio para el primer registro
    fecha_actual = datetime(2025, 10, 20)

    try:
        with open(nombre_archivo, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Escribir la cabecera
            writer.writerow(headers)

            # Generar y escribir cada fila de datos
            for i in range(8, cantidad_registros + 1):
                dni = random.choice(dnis_ejemplo)
                pagada = random.choice([True, False])
                monto = round(random.uniform(20000.00, 35000.00), 2)
                
                # Calcular fechas
                fecha_comienzo = fecha_actual
                # Sumamos un mes aproximadamente para la fecha de fin
                dias_en_mes = (fecha_comienzo.replace(month=fecha_comienzo.month % 12 + 1, day=1) - timedelta(days=1)).day
                fecha_fin = fecha_comienzo + timedelta(days=dias_en_mes -1)

                mes = fecha_comienzo.strftime("%B") # Nombre completo del mes en inglés
                
                nombre_trabajo = random.choice(trabajos_ejemplo)
                nombre_suscripcion = random.choice(suscripciones_ejemplo)
                
                # Escribir la fila en el CSV
                writer.writerow([
                    i,
                    dni,
                    str(pagada).lower(), # Escribe 'true' o 'false'
                    f"{monto:.2f}",
                    fecha_comienzo.strftime("%Y-%m-%d"),
                    fecha_fin.strftime("%Y-%m-%d"),
                    mes,
                    nombre_trabajo,
                    nombre_suscripcion
                ])
                
                # Avanzar al siguiente mes para el próximo registro
                fecha_actual = fecha_fin + timedelta(days=1)
        
        print(f"✅ ¡Éxito! Se ha generado el archivo '{nombre_archivo}' con {cantidad_registros} registros.")

    except IOError as e:
        print(f"❌ Error al escribir el archivo: {e}")

# --- Ejecutar el script ---
if __name__ == "__main__":
    generar_cuotas_csv()