import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import getpass

def enviar_correo_gmail():
    # Configuración
    remitente = "ricardofernandomartinez0@gmail.com"  # Cambia por tu email
    destinatario = "lolfer3@gmail.com"  # Email del destinatario
    asunto = "Correo de prueba desde Python"
    
    # Contenido del mensaje
    mensaje_html = """
    <html>
    <body>
        <h2>¡Hola!</h2>
        <p>Este es un <strong>correo de prueba</strong> enviado desde Python.</p>
        <p>Fecha: {fecha}</p>
        <br>
        <p>Saludos,<br>Tu aplicación</p>
    </body>
    </html>
    """
    
    mensaje_texto = "Este es un correo de prueba enviado desde Python."
    
    # Crear el mensaje
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    
    # Partes del mensaje (texto y HTML)
    parte_texto = MIMEText(mensaje_texto, "plain")
    parte_html = MIMEText(mensaje_html, "html")
    
    mensaje.attach(parte_texto)
    mensaje.attach(parte_html)
    
    try:
        # Solicitar contraseña de forma segura
        password = getpass.getpass("Ingresa tu contraseña de Gmail: ")
        
        # Configurar servidor SMTP de Gmail
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Encriptación TLS
        
        # Iniciar sesión
        server.login(remitente, password)
        
        # Enviar correo
        server.sendmail(remitente, destinatario, mensaje.as_string())
        print("✅ Correo enviado exitosamente!")
        
    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")
    
    finally:
        server.quit()

if __name__ == "__main__":
    enviar_correo_gmail()