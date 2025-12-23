import cv2
import time
from services import state


def test_rtsp_connection(rtsp: str, timeout=3) -> bool:
    cap = cv2.VideoCapture(rtsp)
    start = time.time()

    while time.time() - start < timeout:
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return ret
        time.sleep(0.1)

    cap.release()
    return False


# =========================
# Función para reestablecer la configuración
# =========================
def reset_camera_state():
    with state.cam_lock:
        if state.cam:
            state.cam.liberar()
        state.cam = None

    state.active_rtsp_url = None
    state.camera_dead = False
    state.last_frame_ts = None
    state.last_reconnect_ts = 0

    # Limpia evento para evitar reaperturas fantasma
    state.camera_change_event.clear()
