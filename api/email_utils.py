import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM") or SMTP_USER or "no-reply@santebio.local"

SITIO_URL = os.environ.get("SITIO_URL", "http://localhost:4930")
ADMIN_CORREO_NOTIFICACIONES = os.environ.get("ADMIN_CORREO_NOTIFICACIONES")


def _enviar(destinatario, asunto, cuerpo):
    """Envia un correo, o si no hay credenciales SMTP configuradas
    (SMTP_HOST) -- no hay ningun proveedor de correo conectado
    todavia -- lo imprime en la consola del servidor para poder
    probar el flujo completo en desarrollo. En cuanto se configuren
    SMTP_HOST/SMTP_USER/SMTP_PASSWORD (Gmail con contraseña de
    aplicacion, SendGrid, Resend, etc.) el correo se envia real sin
    tocar nada mas de este archivo."""

    if not SMTP_HOST:
        print("=" * 70, flush=True)
        print("[correo] SMTP no configurado todavía -- modo desarrollo, no se envió un correo real.", flush=True)
        print(f"[correo] Para:    {destinatario}", flush=True)
        print(f"[correo] Asunto:  {asunto}", flush=True)
        print(f"[correo] Cuerpo:\n{cuerpo}", flush=True)
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


def enviar_correo_restablecer(destinatario, token):
    """Envia el correo con el enlace para confirmar el cambio de
    contraseña (valido 30 minutos)."""
    enlace = f"{SITIO_URL}/restablecer.html?token={token}"
    asunto = "Restablece tu contraseña — SanteBio"
    cuerpo = (
        "Recibimos una solicitud para cambiar la contraseña de tu cuenta.\n\n"
        f"Da clic en este enlace para continuar (valido por 30 minutos):\n{enlace}\n\n"
        "Si tú no pediste esto, puedes ignorar este correo — tu contraseña actual sigue funcionando."
    )
    _enviar(destinatario, asunto, cuerpo)


def enviar_correo_confirmacion_pedido(destinatario, folio, items, total):
    """Confirma un pedido nuevo y le da al cliente su folio -- con eso
    (mas su correo) puede consultar el estatus en /seguimiento.html sin
    necesitar cuenta ni sesion."""
    enlace = f"{SITIO_URL}/seguimiento.html?folio={folio}"
    lista_items = "\n".join(f"  - {it.get('qty')}x {it.get('name')}" for it in items)
    asunto = f"Confirmación de tu pedido {folio} — SanteBio"
    cuerpo = (
        f"¡Gracias por tu compra! Tu pedido quedó registrado.\n\n"
        f"Folio de seguimiento: {folio}\n\n"
        f"Productos:\n{lista_items}\n\n"
        f"Total: ${total:,.2f} MXN\n\n"
        f"Puedes consultar el estatus de tu pedido en cualquier momento, sin necesidad de crear una cuenta, aquí:\n{enlace}\n"
        f"(te pedirá tu folio y el correo con el que hiciste la compra)\n\n"
        "Esto es una demo: el pedido ya se guardó en el sistema, pero el cobro no se procesó realmente."
    )
    _enviar(destinatario, asunto, cuerpo)


def enviar_correo_nuevo_pedido_admin(folio, items, total, metodo_pago):
    """Avisa al admin por correo en cuanto entra un pedido nuevo. Si no
    se configuró ADMIN_CORREO_NOTIFICACIONES todavía, simplemente no se
    manda nada (no es un error) -- el aviso en vivo dentro del panel de
    administrador sigue funcionando igual."""
    if not ADMIN_CORREO_NOTIFICACIONES:
        print("[correo] ADMIN_CORREO_NOTIFICACIONES no configurado -- no se notificó por correo al admin.", flush=True)
        return
    lista_items = "\n".join(f"  - {it.get('qty')}x {it.get('name')}" for it in items)
    asunto = f"Nuevo pedido {folio} — SanteBio"
    cuerpo = (
        "Entró un pedido nuevo.\n\n"
        f"Folio: {folio}\n"
        f"Método de pago: {metodo_pago}\n\n"
        f"Productos:\n{lista_items}\n\n"
        f"Total: ${total:,.2f} MXN\n\n"
        f"Revísalo en el panel de administrador: {SITIO_URL}/admin.html"
    )
    _enviar(ADMIN_CORREO_NOTIFICACIONES, asunto, cuerpo)


_MENSAJES_CAMBIO_ESTADO = {
    "Enviado": "tu pedido ya va en camino",
    "Entregado": "tu pedido fue entregado",
    "Cancelado": "tu pedido fue cancelado",
}


def enviar_correo_cambio_estado_pedido(destinatario, folio, estado_nuevo):
    """Avisa al cliente por correo cuando el admin cambia el estatus de
    su pedido a Enviado, Entregado o Cancelado. Los demas estados
    (Pendiente/Aceptado) no generan correo, para no saturar al cliente
    con avisos de pasos intermedios."""
    mensaje_estado = _MENSAJES_CAMBIO_ESTADO.get(estado_nuevo)
    if not mensaje_estado or not destinatario:
        return
    enlace = f"{SITIO_URL}/seguimiento.html?folio={folio}"
    asunto = f"Actualización de tu pedido {folio} — SanteBio"
    cuerpo = (
        f"Te escribimos para avisarte que {mensaje_estado}.\n\n"
        f"Folio: {folio}\n"
        f"Nuevo estatus: {estado_nuevo}\n\n"
        f"Puedes ver el detalle de tu pedido aquí:\n{enlace}\n"
    )
    _enviar(destinatario, asunto, cuerpo)
