from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import cv2

from services import state

router = APIRouter()


async def generar_frames():
    try:
        while True:
            # 🧠 Obtener último frame seguro
            with state.frame_lock:
                frame = None if state.current_frame is None else state.current_frame.copy()

            if frame is None:
                await asyncio.sleep(0.03)
                continue

            ret, jpg = cv2.imencode(".jpg", frame)
            if not ret:
                await asyncio.sleep(0.01)
                continue

            # 📤 Enviar frame MJPEG
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                jpg.tobytes() +
                b"\r\n"
            )

            await asyncio.sleep(0.03)

    except (ConnectionResetError, asyncio.CancelledError, BrokenPipeError):
        # 🔌 El navegador cerró la conexión (normal)
        return

@router.get('/video')
async def video():
    return StreamingResponse(generar_frames(), media_type='multipart/x-mixed-replace; boundary=frame')


