from fastapi import APIRouter
from pydantic import BaseModel

from services.onvif_service import get_rtsp_urls
from services.video_service import test_rtsp_connection
from services import state

router = APIRouter(prefix="/camera", tags=["camera"])


# =====================================================
# MODELOS
# =====================================================

class CameraProbeRequest(BaseModel):
    ip: str
    port: int = 80
    user: str
    password: str


class RTSPRequest(BaseModel):
    rtsp: str


# =====================================================
# ONVIF PROBE POR IP (SIN DISCOVERY)
# =====================================================

@router.post("/onvif-probe")
def onvif_probe(data: CameraProbeRequest):
    """
    Obtiene RTSPs disponibles vía ONVIF usando IP directa.
    """
    try:        
        streams = get_rtsp_urls(
            ip=data.ip,
            port=data.port,
            user=data.user,
            password=data.password
        )


        return {
            "success": True,
            "ip": data.ip,
            "streams": streams
        }

    except Exception as e:
        return {
            "success": False,
            "ip": data.ip,
            "streams": [],
            "error": str(e)
        }


# =====================================================
# PROBAR RTSP (MANUAL U ONVIF)
# =====================================================

@router.post("/test")
def test_camera(data: RTSPRequest):
    """
    Verifica si un RTSP es accesible.
    """
    ok = test_rtsp_connection(data.rtsp)

    return {
        "rtsp": data.rtsp,
        "success": ok
    }


# =====================================================
# ACTIVAR CÁMARA
# =====================================================

@router.post("/select")
def select_camera(data: RTSPRequest):
    """
    Establece el RTSP activo y notifica al hilo de captura.
    """
    state.active_rtsp_url = data.rtsp

    # Notificar al hilo de captura (si existe)
    if hasattr(state, "camera_change_event") and state.camera_change_event:
        state.camera_change_event.set()

    return {
        "success": True,
        "active_rtsp": data.rtsp
    }


# =====================================================
# CÁMARA ACTUAL
# =====================================================

@router.get("/current")
def get_current_camera():
    """
    Devuelve la cámara RTSP actualmente activa.
    """
    return {
        "rtsp": state.active_rtsp_url
    }
