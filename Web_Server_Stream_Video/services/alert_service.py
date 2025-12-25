import smtplib
import requests
import os
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime
import urllib.parse
import cv2

load_dotenv()

def frame_to_jpeg_bytes(frame, quality=85):
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode(".jpg", frame, encode_params)

    if not success:
        raise Exception("No se pudo codificar la imagen")

    return buffer.tobytes()

def send_email_alert_1(frame):
    img_bytes = frame_to_jpeg_bytes(frame)

    msg = EmailMessage()
    msg["From"] = "sstestmail2026@gmail.com"
    msg["To"] = "duendenener@gmail.com"
    msg["Subject"] = "🚨 Alerta del Sistema de Monitoreo IA"

    msg.set_content(
        f"Evento detectado\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    msg.add_attachment(
        img_bytes,
        maintype="image",
        subtype="jpeg",
        filename="alerta.jpg"
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("sstestmail2026@gmail.com", "wlop zwla kudi xajx")
        smtp.send_message(msg)


def send_email_alert_2():
    to = "duendenener@gmail.com"
    subject = "🚨 Alerta del Sistema IA"

    body = f"""
ALERTA DEL SISTEMA DE MONITOREO IA
Evento detectado
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

    url = (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={urllib.parse.quote(to)}"
        f"&su={urllib.parse.quote(subject)}"
        f"&body={urllib.parse.quote(body)}"
    )

    return {
        "url": url
    }


def send_whatsapp_alert_1():
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

    response = requests.post(url, json=payload, headers=headers, timeout=10)

    if response.status_code not in (200, 201):
        raise Exception(
            f"WhatsApp API error {response.status_code}: {response.text}"
        )

    return response.json()



def send_whatsapp_alert_2():
    phone = "50684926004"

    message = f"""
ALERTA DEL SISTEMA DE MONITOREO IA
Evento detectado
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

    encoded_message = urllib.parse.quote(message)

    url = (
        f"https://web.whatsapp.com/send"
        f"?phone={phone}&text={encoded_message}"
    )

    return {
        "url": url
    }
