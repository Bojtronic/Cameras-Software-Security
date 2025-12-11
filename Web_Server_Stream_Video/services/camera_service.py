import cv2
import threading


class Camara:
    def __init__(self, fuente, buffer_size=5):
        self.cap = cv2.VideoCapture(fuente)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
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
