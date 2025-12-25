from fastapi import APIRouter
from services.alert_service import send_email_alert_1, send_whatsapp_alert_1, send_email_alert_2, send_whatsapp_alert_2
from services import state

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/sendWhatsApp1")
def send_alert_whatsapp_1():
    try:
        result = send_whatsapp_alert_1()
        return {
            "success": True,
            "provider": "whatsapp-cloud",
            "response": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sendWhatsApp2")
def send_alert_whatsapp_2():
    try:
        result = send_whatsapp_alert_2()
        return {
            "success": True,
            "url": result["url"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/sendEmail1")
def send_alert_email_1():
    try:
        # Obtener último frame con lock
        with state.frame_lock:
            frame = state.current_frame

        if frame is None:
            return {
                "success": False,
                "error": "No hay frame disponible todavía"
            }

        send_email_alert_1(frame)

        return {
            "success": True,
            "provider": "smtp-gmail"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sendEmail2")
def send_alert_email_2():
    try:
        result = send_email_alert_2()
        return {
            "success": True,
            "url": result["url"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }