import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD.get_secret_value()
        self.frontend_url = settings.FRONTEND_URL
        self.backend_url = settings.BACKEND_URL
    
    async def send_email(self, to_email: str, subject: str, body_html: str) -> bool:
        """Función para enviar emails usando SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body_html, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Error enviando email: {e}")
            return False
    
    async def send_verification_email(self, email: str, token: str) -> bool:
        """Envía email de verificación"""
        subject = "Verifica tu cuenta - Gimnasio Abito"
        verification_url = f"{self.frontend_url}/verify-email?token={token}"
        
        body_html = f"""
        <html>
        <body>
            <h2>¡Bienvenido a Gimnasio Abito!</h2>
            <p>Para completar tu registro, por favor verifica tu dirección de email haciendo clic en el siguiente enlace:</p>
            <p><a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verificar Email</a></p>
            <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
            <p>{verification_url}</p>
            <p>Este enlace expirará en 24 horas.</p>
            <br>
            <p>Si no solicitaste este registro, ignora este mensaje.</p>
        </body>
        </html>
        """
        
        return await self.send_email(email, subject, body_html)
    
    async def send_password_reset_email(self, email: str, token: str) -> bool:
        """Envía email para resetear contraseña"""
        subject = "Restablecer contraseña - Gimnasio Abito"
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        body_html = f"""
        <html>
        <body>
            <h2>Restablecer contraseña</h2>
            <p>Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:</p>
            <p><a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer Contraseña</a></p>
            <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
            <p>{reset_url}</p>
            <p>Este enlace expirará en 1 hora.</p>
            <br>
            <p>Si no solicitaste restablecer tu contraseña, ignora este mensaje.</p>
        </body>
        </html>
        """
        
        return await self.send_email(email, subject, body_html)
    
    async def send_welcome_email(self, email: str, nombre: str) -> bool:
        """Envía email de bienvenida después de registro completo"""
        subject = "¡Bienvenido a Gimnasio Abito!"
        
        body_html = f"""
        <html>
        <body>
            <h2>¡Hola {nombre}!</h2>
            <p>Te damos la bienvenida a Gimnasio Abito. Tu registro se ha completado exitosamente.</p>
            <p>Ahora puedes acceder a todos nuestros servicios y comenzar tu journey fitness.</p>
            <br>
            <p>¡Nos vemos en el gimnasio!</p>
            <p>El equipo de Gimnasio Abito</p>
        </body>
        </html>
        """
        
        return await self.send_email(email, subject, body_html)

# Instancia global del servicio de email
email_service = EmailService()
