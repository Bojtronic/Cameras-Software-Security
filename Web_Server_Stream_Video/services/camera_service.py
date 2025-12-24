import cv2
import threading
import time


class Camara:
    def __init__(self, fuente=None, buffer_size=5):
        self.fuente = fuente
        self.buffer_size = buffer_size
        self.lock = threading.Lock()
        self.cap = None
        self.last_open_try = 0

    def _open(self):
        now = time.time()

        # 🛑 no intentar abrir en loop (protege CPU)
        if now - self.last_open_try < 1.0:
            return False

        self.last_open_try = now

        try:
            cap = cv2.VideoCapture(self.fuente, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                cap.release()
                return False

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            except:
                pass

            self.cap = cap
            return True

        except:
            return False

    def obtener_frame(self):
        with self.lock:

            if not self.fuente:
                return None

            # 🔄 Abrir si no existe
            if self.cap is None:
                if not self._open():
                    return None

            ret, frame = self.cap.read()

            # 💥 RTSP muerto → destruir socket
            if not ret or frame is None:
                self._close()
                return None

            return frame

    def _close(self):
        try:
            if self.cap:
                self.cap.release()
        except:
            pass
        self.cap = None

    def liberar(self):
        with self.lock:
            self._close()
