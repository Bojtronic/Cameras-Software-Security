# person_detection_server.py

import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import cv2
import threading
from typing import Optional, Union
from contextlib import asynccontextmanager
import uvicorn
import numpy as np

# Importar detector de persona
from person_detector import PersonDetector

camara = None
detector = None  # Detector de persona

# --------------------------------------------------------
#  Lifespan
# --------------------------------------------------------
@asynccontextmanager
async def duracion_app(app: FastAPI):
    """
    Maneja eventos de inicio y cierre de la aplicación.
    """
    try:
        yield
    except asyncio.exceptions.CancelledError as error:
        print(error.args)
    finally:
        if camara:
            camara.liberar()
            print("Recurso de cámara liberado.")

app = FastAPI(lifespan=duracion_app)

# --------------------------------------------------------
#  Clase Cámara
# --------------------------------------------------------
class Camara:
    """
    Clase para manejar la captura de video desde una cámara.
    """

    def __init__(self, fuente: Optional[Union[str, int]] = 0) -> None:
        self.cap = cv2.VideoCapture(fuente)
        self.lock = threading.Lock()

    def obtener_frame(self) -> Optional[np.ndarray]:
        """
        Devuelve el frame como array BGR (NO JPEG codificado)
        para poder procesarlo con OpenCV y Mediapipe.
        """
        with self.lock:
            ret, frame = self.cap.read()
            if not ret:
                return None
            return frame

    def liberar(self) -> None:
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()

# --------------------------------------------------------
#  Endpoints
# --------------------------------------------------------
@app.get("/")
async def raiz():
    return JSONResponse({"mensaje": "Servidor de detección funcionando. Accede a /persona."})

@app.get("/persona")
async def detectar_persona():
    """
    Endpoint que detecta si una persona está presente en el frame actual.
    """
    frame = camara.obtener_frame()

    if frame is None:
        return JSONResponse({"persona_detectada": False, "error": "No se pudo obtener frame."})

    presente, _ = detector.hay_persona(frame)

    return JSONResponse({"persona_detectada": presente})

# --------------------------------------------------------
#  Servidor
# --------------------------------------------------------
async def ejecutar_servidor():
    config = uvicorn.Config(app, host='192.168.18.26', port=8010, log_level="info")
    servidor = uvicorn.Server(config)
    await servidor.serve()

# --------------------------------------------------------
#  Main
# --------------------------------------------------------
if __name__ == '__main__':

    # Inicializar cámara
    camara = Camara('rtsp://admin:TIss9831@192.168.18.14:554/')

    # Inicializar detector
    detector = PersonDetector(dibujar=False)

    print("Servidor iniciado en http://192.168.18.26:8010/persona")

    try:
        asyncio.run(ejecutar_servidor())
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
