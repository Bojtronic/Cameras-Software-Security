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
        model_complexity=config.MODEL_COMPLEXITY,
        enable_segmentation=config.ENABLE_SEGMENTATION,
        smooth_landmarks=config.SMOOTH_LANDMARKS,
        dibujar=config.DIBUJAR,
        
        min_body_height = config.MIN_BODY_HEIGHT,
        aspect_ratio_lying = config.ASPECT_RATIO_LYING,
        max_angle_standing = config.MAX_ANGLE_STANDING,
        min_angle_lying = config.MIN_ANGLE_LYING,
        head_tilt_min_standing = config.HEAD_TILT_MIN_STANDING,
        com_y_standing_max = config.COM_Y_STANDING_MAX,
        com_y_sitting_max = config.COM_Y_SITTING_MAX
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

    prev_pose = None
    prev_pose_ts = None
    confirmar_caida_frames = 0
    CAIDA_CONFIRMADA = False


    # ===== Thread principal =====
    def capture_and_process():
        nonlocal prev_pose, prev_pose_ts, confirmar_caida_frames, CAIDA_CONFIRMADA

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
            pose_name = "desconocido"

            # ======================================================
            # 👤 PERSONA PRESENTE → CLASIFICAR POSE
            # ======================================================
            if persona_real and present:

                # Clasificación usando features ya calculadas
                pose_name = detector.clasificar_pose(result)

                now = time.time()
                caida_detectada = False

                # ----------------------------------
                # Detección de transición rápida (caída)
                # ----------------------------------
                if prev_pose is not None and prev_pose_ts is not None:
                    transition_time = now - prev_pose_ts

                    if (
                        prev_pose in ("de_pie", "sentado")
                        and pose_name == "acostado"
                        and transition_time < 1.2
                    ):
                        caida_detectada = True

                # Confirmación por frames consecutivos
                if caida_detectada:
                    confirmar_caida_frames += 1
                else:
                    confirmar_caida_frames = 0

                CAIDA_CONFIRMADA = confirmar_caida_frames >= 3

                # Actualizar pose previa solo si es estable
                if pose_name != "desconocido" and not CAIDA_CONFIRMADA:
                    prev_pose = pose_name
                    prev_pose_ts = now

                # ----------------------------------
                # Visualización
                # ----------------------------------
                if result.get("landmarks") is not None:
                    draw_pose_on_frame(frame_to_stream, result["landmarks"])

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

                if CAIDA_CONFIRMADA:
                    with state.caida_lock:
                        if not state.caida_activa:
                            state.caida_activa = True
                            state.caida_ts = now

                    cv2.putText(
                        frame_to_stream,
                        "!!! CAIDA DETECTADA !!!",
                        (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.3,
                        (0, 0, 255),
                        4
                    )

            # ======================================================
            # 🚫 NO HAY PERSONA REAL
            # ======================================================
            else:
                with state.caida_lock:
                    state.caida_activa = False
                    state.caida_ts = None

                prev_pose = None
                prev_pose_ts = None
                confirmar_caida_frames = 0
                CAIDA_CONFIRMADA = False

                cv2.putText(
                    frame_to_stream,
                    "NO HAY PERSONA",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (200, 200, 200),
                    2
                )

            # ======================================================
            # 📤 Publicar frame y resultados
            # ======================================================
            with state.frame_lock:
                state.current_frame = frame_to_stream
                state.latest_result = {
                    "timestamp": time.time(),
                    "persona_real": persona_real,
                    "present": present,
                    "pose": pose_name,
                    "caida": CAIDA_CONFIRMADA,

                    # Métricas útiles (debug / telemetría)
                    "visibility_count": result.get("visibility_count"),
                    "body_height": result.get("body_height"),
                    "aspect_ratio": result.get("aspect_ratio"),
                    "angle_from_vertical": result.get("angle_from_vertical"),
                    "center_of_mass_y": result.get("center_of_mass_y"),
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

