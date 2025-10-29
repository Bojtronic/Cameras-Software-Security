import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, JSONResponse
import cv2
import threading
from typing import AsyncGenerator, Optional, Union
from contextlib import asynccontextmanager
import uvicorn

camara = None  # Será inicializada más adelante

@asynccontextmanager
async def duracion_app(app: FastAPI):
    """
    Context manager para manejar los eventos de inicio y cierre de la aplicación.
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

class Camara:
    """
    Clase para manejar la captura de video desde una cámara.
    """

    def __init__(self, fuente: Optional[Union[str, int]] = 0) -> None:
        """
        Inicializa la cámara.

        :param fuente: Índice de la cámara o URL RTSP.
        """
        self.cap = cv2.VideoCapture(fuente)
        self.lock = threading.Lock()

    def obtener_frame(self) -> bytes:
        """
        Captura un frame de la cámara.

        :return: Imagen codificada en JPEG como bytes.
        """
        with self.lock:
            ret, frame = self.cap.read()
            if not ret:
                return b''

            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                return b''

            return jpeg.tobytes()

    def liberar(self) -> None:
        """
        Libera el recurso de la cámara.
        """
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()

async def generar_frames() -> AsyncGenerator[bytes, None]:
    """
    Generador asincrónico que produce frames de la cámara.
    """
    try:
        while True:
            frame = camara.obtener_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                await asyncio.sleep(0.1)  # Espera un poco si no hay frame
            await asyncio.sleep(0)
    except (asyncio.CancelledError, GeneratorExit):
        print("Generación de frames cancelada.")
    finally:
        print("Generador de frames finalizado.")

@app.get("/")
async def raiz():
    """
    Endpoint raíz para verificar que el servidor está funcionando.
    """
    return JSONResponse({"mensaje": "Servidor de video funcionando. Accede a /video para ver el streaming."})

@app.get("/video")
async def transmision_video() -> StreamingResponse:
    """
    Endpoint para transmitir video en tiempo real.
    """
    return StreamingResponse(
        generar_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@app.get("/snapshot")
async def obtener_snapshot() -> Response:
    """
    Endpoint para capturar un frame único.
    """
    frame = camara.obtener_frame()
    if frame:
        return Response(content=frame, media_type="image/jpeg")
    else:
        return Response(status_code=404, content="No se pudo obtener el frame de la cámara.")

async def ejecutar_servidor():
    """
    Función principal para ejecutar el servidor Uvicorn.
    """
    config = uvicorn.Config(app, host='192.168.18.26', port=8007, log_level="info")
    servidor = uvicorn.Server(config)
    await servidor.serve()

if __name__ == '__main__':

    # Inicializa la cámara con RTSP o cámara local
    # camara = Camera()

    # Inicializa la cámara para un indice especifico
    # camara = Camara(0)

    # camara = Camera('rtsp://user:password@ip_address:port/') 
    # camara = Camera('rtsp://rtspstream:2513C6jGcJo93gwHw0X52@zephyr.rtsp.stream/people')
    camara = Camara('rtsp://admin:TIss9831@192.168.18.14:554/')

    print("Servidor iniciado. Abre tu navegador en http://localhost:8007 o http://<tu_IP>:8007")
    try:
        asyncio.run(ejecutar_servidor())
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
