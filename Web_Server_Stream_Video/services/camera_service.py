import cv2
import threading


class Camara:
    def __init__(self, fuente, buffer_size=5):
        self.cap = cv2.VideoCapture(fuente)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
            self.cap.set(cv2.CAP_PROP_FPS, 30)                   # Depende de la cámara
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)             # Evita acumulación en algunos drivers
        except Exception:
            pass
        self.lock = threading.Lock()

    def obtener_frame(self):
        with self.lock:
            ret, frame = self.cap.read()
            return frame if ret else None

    def liberar(self):
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()
