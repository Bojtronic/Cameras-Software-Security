import threading
import time

# Estado compartido entre hilo de captura y rutas
frame_lock = threading.Lock()
process_lock = threading.Lock()
current_frame = None
latest_result = None
latest_result_ts = 0.0

# Instancias inicializadas en app/events.py
camara = None
detector = None
presence_controller = None
running_event = None

# Utilidad para inicializar desde events
def set_dependencies(cam, det, presence, run_event):
    global camara, detector, presence_controller, running_event
    camara = cam
    detector = det
    presence_controller = presence
    running_event = run_event
