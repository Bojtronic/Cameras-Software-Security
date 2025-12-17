import smtplib
import requests
import os
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def send_email_alert():
    msg = EmailMessage()
    #msg["From"] = os.getenv("EMAIL_USER")
    #msg["To"] = os.getenv("EMAIL_TO")
    msg["Subject"] = "🚨 Alerta del Sistema de Monitoreo IA"

    body = f"""
ALERTA DEL SISTEMA DE MONITOREO IA

Evento detectado automáticamente.
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        smtp.send_message(msg)


def send_whatsapp_alert():
    url = f"https://graph.facebook.com/v19.0/{os.getenv('WA_PHONE_ID')}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": os.getenv("WA_TO"),
        "type": "text",
        "text": {
            "body": (
                "🚨 *ALERTA DEL SISTEMA DE MONITOREO IA*\n\n"
                "Evento detectado automáticamente.\n"
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        }
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('WA_TOKEN')}",
        "Content-Type": "application/json"
    }

    requests.post(url, json=payload, headers=headers, timeout=10)
