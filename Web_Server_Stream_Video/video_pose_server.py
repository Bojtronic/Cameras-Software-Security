import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
import threading
import cv2
import uvicorn
import numpy as np
import mediapipe as mp


# ============================================================
#   MEDIAPIPE POSE DETECTOR (CONFIGURACIÓN MÁS ESTABLE)
# ============================================================
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

pose = mp_pose.Pose(
    static_image_mode=False,
    min_detection_confidence=0.65,   # más estricto
    min_tracking_confidence=0.65     # más estricto
)


# ============================================================
#   SISTEMA ANTI FALSOS POSITIVOS
# ============================================================
PERSONA_MIN_LANDMARKS = 8       # mínimo de puntos confiables
PERSONA_FRAMES_ON = 3           # cuántos frames consecutivos para activar
PERSONA_FRAMES_OFF = 3          # cuántos frames consecutivos para desactivar

contador_on = 0
contador_off = 0
persona_real = False


def pose_confiable(landmarks):
    """
    Verifica que haya suficientes puntos confiables (visibility/presence > 0.5)
    Esto reduce MUCHO los falsos positivos.
    """
    puntos = 0
    for lm in landmarks.landmark:
        if lm.visibility > 0.5 or lm.presence > 0.5:
            puntos += 1
    return puntos >= PERSONA_MIN_LANDMARKS


# ============================================================
#        FASTAPI + CAMARA
# ============================================================
camara = None


class Camara:
    def __init__(self, fuente=0):
        self.cap = cv2.VideoCapture(fuente)
        self.lock = threading.Lock()

    def obtener_frame(self):
        with self.lock:
            ret, frame = self.cap.read()
            if not ret:
                return None
            return frame

    def liberar(self):
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if camara:
        camara.liberar()
        print("Cámara liberada.")


app = FastAPI(lifespan=lifespan)


# ============================================================
#        PROCESAR FRAME (CON FILTROS ANTI FANTASMA)
# ============================================================
def procesar_frame(frame):
    global contador_on, contador_off, persona_real

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)

    persona_confiable = False

    if results.pose_landmarks and pose_confiable(results.pose_landmarks):
        persona_confiable = True

    # ---- SISTEMA ANTI FANTASMA ----
    if persona_confiable:
        contador_on += 1
        contador_off = 0
        if contador_on >= PERSONA_FRAMES_ON:
            persona_real = True
    else:
        contador_off += 1
        contador_on = 0
        if contador_off >= PERSONA_FRAMES_OFF:
            persona_real = False

    # ---- DIBUJAR SOLO SI ES REAL ----
    if persona_real:
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )
        cv2.putText(
            frame,
            "PERSONA DETECTADA",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3
        )

    return frame, persona_real


# ============================================================
#        STREAMING EN /video
# ============================================================
async def generar_frames():
    while True:
        frame = camara.obtener_frame()

        if frame is None:
            await asyncio.sleep(0.05)
            continue

        frame_procesado, _ = procesar_frame(frame)

        ret, jpg = cv2.imencode(".jpg", frame_procesado)
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
        )

        await asyncio.sleep(0)


# ============================================================
#        ENDPOINTS
# ============================================================
@app.get("/")
async def raiz():
    return JSONResponse({"mensaje": "Servidor funcionando. Ir a /video"})


@app.get("/video")
async def video():
    return StreamingResponse(
        generar_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/estado")
async def estado():
    """Devuelve si hay persona REAL detectada (con filtros)."""
    return {"persona_detectada": persona_real}


# ============================================================
#        MAIN
# ============================================================
if __name__ == "__main__":

    camara = Camara("rtsp://admin:TIss9831@192.168.18.14:554/")

    print("Servidor iniciado → http://192.168.18.26:8007/video")

    uvicorn.run(app, host="192.168.18.26", port=8007)

#################