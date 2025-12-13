from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import cv2

from services import state

router = APIRouter()


async def generar_frames():
    while True:
        with state.frame_lock:
            frame = None if state.current_frame is None else state.current_frame.copy()

        if frame is None:
            await asyncio.sleep(0.03)
            continue

        ret, jpg = cv2.imencode('.jpg', frame)
        if not ret:
            await asyncio.sleep(0.01)
            continue

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
        await asyncio.sleep(0.03)


@router.get('/video')
async def video():
    return StreamingResponse(generar_frames(), media_type='multipart/x-mixed-replace; boundary=frame')


@router.post("/select")
def select_camera(rtsp_url: str):
    """
    Cambia la cámara activa en tiempo real
    """
    state.active_rtsp_url = rtsp_url

    if state.camera_change_event:
        state.camera_change_event.set()

    return {
        "status": "ok",
        "active_rtsp": rtsp_url
    }


