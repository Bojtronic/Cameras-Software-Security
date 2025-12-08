import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf')

import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
import threading
import cv2
import uvicorn
import numpy as np
import mediapipe as mp
import time

from person_detector import PersonDetector

RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/"
CAP_BUFFERSIZE = 5

DETECTION_CONF = 0.7
TRACKING_CONF = 0.7
VIS_THRESH = 0.7
MIN_LANDMARKS = 10
HOMBROS_MIN_PX = 40
HOMBROS_MAX_PX = 1000

FRAMES_ON = 5
FRAMES_OFF = 5

POSE_COLORS = {
    "de_pie": (0, 255, 0),
    "sentado": (0, 200, 255),
    "acostado": (255, 200, 0),
    "dormido": (255, 0, 255),
    "caido": (0, 0, 255),
    "desconocido": (200, 200, 200)
}

camara = None
detector = None

frame_lock = threading.Lock()
process_lock = threading.Lock()
current_frame = None
latest_result = None
latest_result_ts = 0.0

persona_real = False
contador_on = 0
contador_off = 0


class Camara:
    def __init__(self, fuente):
        self.cap = cv2.VideoCapture(fuente)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAP_BUFFERSIZE)
        except:
            pass
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
    global camara, detector

    camara = Camara(RTSP_URL)
    detector = PersonDetector(
        min_detection_conf=DETECTION_CONF,
        min_tracking_conf=TRACKING_CONF,
        vis_thresh=VIS_THRESH,
        min_visible_landmarks=MIN_LANDMARKS,
        hombros_min_px=HOMBROS_MIN_PX,
        hombros_max_px=HOMBROS_MAX_PX,
        dibujar=False
    )

    running_event = threading.Event()
    running_event.set()

    def capture_and_process():
        global current_frame, latest_result, latest_result_ts
        global persona_real, contador_on, contador_off

        while running_event.is_set():

            frame = camara.obtener_frame()
            if frame is None:
                time.sleep(0.03)
                continue

            with process_lock:
                result = detector.analyze(frame)

            present = result.get("present", False)

            if present:
                contador_on += 1
                contador_off = 0
                if contador_on >= FRAMES_ON:
                    persona_real = True
            else:
                contador_off += 1
                contador_on = 0
                if contador_off >= FRAMES_OFF:
                    persona_real = False

            frame_to_stream = frame.copy()
            pose_name = None

            if persona_real and result.get("landmarks") is not None:
                lm = result["landmarks"]

                pose_name = detector.clasificar_pose(
                    lm,
                    img_w=frame.shape[1],
                    img_h=frame.shape[0]
                )

                mp.solutions.drawing_utils.draw_landmarks(
                    frame_to_stream,
                    lm,
                    mp.solutions.pose.POSE_CONNECTIONS,
                    mp.solutions.drawing_utils.DrawingSpec(thickness=2, circle_radius=2),
                    mp.solutions.drawing_utils.DrawingSpec(thickness=2)
                )

                color = POSE_COLORS.get(pose_name, (200, 200, 200))
                cv2.putText(frame_to_stream,
                            f"POSE: {pose_name.upper()}",
                            (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.2,
                            color,
                            3
                            )
            else:
                cv2.putText(frame_to_stream, "SIN PERSONA REAL",
                            (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200,200,200), 2)

            with frame_lock:
                current_frame = frame_to_stream
                latest_result = {
                    "timestamp": time.time(),
                    "persona_real": persona_real,
                    "present": present,
                    "pose": pose_name,
                    "visibility_count": result.get("visibility_count"),
                    "head_tilt": result.get("head_tilt"),
                    "shoulder_px": result.get("shoulder_px"),
                    "angle_torso_deg": result.get("angle_torso_deg")
                }
                latest_result_ts = latest_result["timestamp"]

            time.sleep(0.01)

    th = threading.Thread(target=capture_and_process, daemon=True)
    th.start()

    try:
        yield
    finally:
        running_event.clear()
        time.sleep(0.2)
        camara.liberar()


app = FastAPI(lifespan=lifespan)


async def generar_frames():
    while True:
        with frame_lock:
            frame = None if current_frame is None else current_frame.copy()

        if frame is None:
            await asyncio.sleep(0.03)
            continue

        ret, jpg = cv2.imencode(".jpg", frame)
        if not ret:
            await asyncio.sleep(0.01)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            jpg.tobytes() +
            b"\r\n"
        )
        await asyncio.sleep(0.03)



@app.get("/")
async def root():
    return {"msg": "Servidor OK — visitar /video /persona /pose"}


@app.get("/video")
async def video():
    return StreamingResponse(generar_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/persona")
async def persona():
    with frame_lock:
        res = latest_result.copy() if latest_result else None

    if res is None:
        return {"persona_detectada": False, "pose": None}

    return {
        "persona_detectada": res["persona_real"],
        "pose": res["pose"],
        "meta": {
            "visibility_count": res.get("visibility_count"),
            "head_tilt": res.get("head_tilt"),
            "shoulder_px": res.get("shoulder_px"),
            "angle_torso_deg": res.get("angle_torso_deg")
        }
    }


@app.get("/pose")
async def pose_endpoint():
    with frame_lock:
        res = latest_result.copy() if latest_result else None

    if res is None:
        return {"persona_detectada": False, "pose": None}

    return {"persona_detectada": res["persona_real"], "pose": res["pose"]}



if __name__ == "__main__":
    print("Servidor en http://0.0.0.0:8010/video")
    uvicorn.run(app, host="0.0.0.0", port=8010)
