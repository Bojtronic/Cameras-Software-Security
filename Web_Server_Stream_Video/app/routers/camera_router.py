from fastapi import APIRouter
from pydantic import BaseModel

from services.onvif_service import get_rtsp_urls
from services.video_service import test_rtsp_connection, reset_camera_state
from services import state
from services.network_scan_service import scan_network, get_local_subnet
from app.models.network_scan import NetworkScanRequest


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
    rtsp = data.rtsp.strip()

    if not rtsp.lower().startswith("rtsp://"):
        return {"success": False, "error": "RTSP inválido"}

    if not test_rtsp_connection(rtsp):
        state.active_rtsp_url = None
        state.camera_change_event.set()   #forzar desconexión 
        return {"success": False, "error": "No se pudo conectar"}

    state.active_rtsp_url = rtsp
    state.camera_change_event.set()
    return {"success": True}



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


@router.post("/network-scan")
def network_scan():
    subnet = get_local_subnet()
    cameras = scan_network(subnet)
    return {
        "success": True,
        "devices": cameras,
        "subnet": subnet
    }
    
    