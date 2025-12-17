from fastapi import APIRouter
from services.alert_service import send_email_alert, send_whatsapp_alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/send")
def send_alert():
    try:
        send_email_alert()
        #send_whatsapp_alert()
        return {"success": True}
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
