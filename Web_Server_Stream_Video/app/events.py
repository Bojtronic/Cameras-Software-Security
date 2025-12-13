import threading
import time
from contextlib import asynccontextmanager

import cv2

from core import config
from detectors.person_detector import PersonDetector
from services.camera_service import Camara
from services.person_service import PersonPresenceController
from services.pose_service import draw_pose_on_frame, get_pose_color
from services import state


@asynccontextmanager
async def lifespan(app):
    """
    Inicializa la camara, detector y arranca el hilo de captura/procesado.
    """

    # ===== Cámara inicial (por defecto) =====
    state.set_active_camera(config.RTSP_URL)

    with state.cam_lock:
        state.cam = Camara(
            state.active_rtsp_url,
            buffer_size=config.CAP_BUFFERSIZE
        )

    # ===== Detector =====
    detector = PersonDetector(
        min_detection_conf=config.DETECTION_CONF,
        min_tracking_conf=config.TRACKING_CONF,
        vis_thresh=config.VIS_THRESH,
        min_visible_landmarks=config.MIN_LANDMARKS,
        hombros_min_px=config.HOMBROS_MIN_PX,
        hombros_max_px=config.HOMBROS_MAX_PX,
        dibujar=False
    )

    presence = PersonPresenceController(
        config.FRAMES_ON,
        config.FRAMES_OFF
    )

    running_event = threading.Event()
    running_event.set()

    state.running_event = running_event
    state.detector = detector
    state.presence = presence

    # Evento para cambio de cámara
    state.camera_change_event = threading.Event()

    # ===== Thread principal =====
    def capture_and_process():
        while running_event.is_set():

            # 🔁 Cambio de cámara solicitado
            if state.camera_change_event.is_set():
                with state.cam_lock:
                    if state.cam:
                        state.cam.liberar()
                    state.cam = Camara(
                        state.active_rtsp_url,
                        buffer_size=config.CAP_BUFFERSIZE
                    )
                state.camera_change_event.clear()
                time.sleep(0.1)
                continue

            # 🎥 Obtener frame
            with state.cam_lock:
                cam = state.cam

            if cam is None:
                time.sleep(0.05)
                continue

            frame = cam.obtener_frame()
            if frame is None:
                time.sleep(0.03)
                continue

            # 🧠 Procesamiento IA
            with state.process_lock:
                result = detector.analyze(frame)

            present = result.get("present", False)
            persona_real = presence.update(present)

            frame_to_stream = frame.copy()
            pose_name = None

            if persona_real and result.get("landmarks") is not None:
                lm = result["landmarks"]
                pose_name = detector.clasificar_pose(
                    lm,
                    img_w=frame.shape[1],
                    img_h=frame.shape[0]
                )

                draw_pose_on_frame(frame_to_stream, lm)
                color = get_pose_color(pose_name)

                cv2.putText(
                    frame_to_stream,
                    f"POSE: {pose_name.upper()}",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    color,
                    3
                )
            else:
                cv2.putText(
                    frame_to_stream,
                    "NO HAY PERSONA",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (200, 200, 200),
                    2
                )

            # 📤 Publicar frame
            with state.frame_lock:
                state.current_frame = frame_to_stream
                state.latest_result = {
                    "timestamp": time.time(),
                    "persona_real": persona_real,
                    "present": present,
                    "pose": pose_name,
                    "visibility_count": result.get("visibility_count"),
                    "head_tilt": result.get("head_tilt"),
                    "shoulder_px": result.get("shoulder_px"),
                    "angle_torso_deg": result.get("angle_torso_deg")
                }
                state.latest_result_ts = state.latest_result["timestamp"]

            time.sleep(0.005)

    # 🚀 Arrancar thread
    th = threading.Thread(target=capture_and_process, daemon=True)
    th.start()

    try:
        yield
    finally:
        running_event.clear()
        time.sleep(0.2)
        with state.cam_lock:
            if state.cam:
                state.cam.liberar()

