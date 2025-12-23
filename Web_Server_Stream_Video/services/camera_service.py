import cv2
import threading
import time


class Camara:
    def __init__(self, fuente=None, buffer_size=5):
        self.fuente = fuente
        self.buffer_size = buffer_size
        self.lock = threading.Lock()
        self.cap = None

    def _open(self):
        if not self.fuente:
            return False

        cap = cv2.VideoCapture(self.fuente, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap.release()
            return False

        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
        except Exception:
            pass

        self.cap = cap
        return True

    def obtener_frame(self):
        with self.lock:

            # 🚫 No hay fuente → no intentar abrir
            if not self.fuente:
                return None

            # 🔓 Abrir solo si es necesario
            if self.cap is None:
                if not self._open():
                    return None

            ret, frame = self.cap.read()

            # 🔄 Error de lectura → forzar reapertura
            if not ret:
                self._close()
                return None

            return frame

    def actualizar_fuente(self, nueva_fuente):
        """
        Cambia RTSP en caliente sin reiniciar el sistema
        """
        with self.lock:
            self._close()
            self.fuente = nueva_fuente

    def _close(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def liberar(self):
        """
        Alias seguro
        """
        with self.lock:
            self._close()
            
