import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM") or SMTP_USER or "no-reply@santebio.local"

SITIO_URL = os.environ.get("SITIO_URL", "http://localhost:4930")


def enviar_correo_restablecer(destinatario, token):
    """Envia el correo con el enlace para confirmar el cambio de
    contraseña. Si no hay credenciales SMTP configuradas (SMTP_HOST),
    no hay ningun proveedor de correo conectado todavia: en vez de
    fallar, se imprime el enlace en la consola del servidor para poder
    probar el flujo completo en desarrollo. En cuanto se configuren
    SMTP_HOST/SMTP_USER/SMTP_PASSWORD (Gmail con contraseña de
    aplicacion, SendGrid, Resend, etc.) el correo se envia real sin
    tocar nada mas de este archivo."""

    enlace = f"{SITIO_URL}/restablecer.html?token={token}"
    asunto = "Restablece tu contraseña — SanteBio"
    cuerpo = (
        "Recibimos una solicitud para cambiar la contraseña de tu cuenta.\n\n"
        f"Da clic en este enlace para continuar (valido por 30 minutos):\n{enlace}\n\n"
        "Si tú no pediste esto, puedes ignorar este correo — tu contraseña actual sigue funcionando."
    )

    if not SMTP_HOST:
        print("=" * 70, flush=True)
        print("[correo] SMTP no configurado todavía -- modo desarrollo, no se envió un correo real.", flush=True)
        print(f"[correo] Para:    {destinatario}", flush=True)
        print(f"[correo] Asunto:  {asunto}", flush=True)
        print(f"[correo] Enlace:  {enlace}", flush=True)
        print("=" * 70, flush=True)
        return

    mensaje = MIMEText(cuerpo)
    mensaje["Subject"] = asunto
    mensaje["From"] = SMTP_FROM
    mensaje["To"] = destinatario

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [destinatario], mensaje.as_string())
