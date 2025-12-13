import cv2
import threading


class Camara:
    def __init__(self, fuente, buffer_size=5):
        self.fuente = fuente
        self.buffer_size = buffer_size
        self.lock = threading.Lock()
        self.cap = None
        self._open()

    def _open(self):
        self.cap = cv2.VideoCapture(self.fuente)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
        except Exception:
            pass

    def obtener_frame(self):
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                self._open()

            ret, frame = self.cap.read()
            if not ret:
                return None

            return frame

    def liberar(self):
        """
        Libera correctamente la cámara (RTSP / USB).
        Seguro para multihilo.
        """
        with self.lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
