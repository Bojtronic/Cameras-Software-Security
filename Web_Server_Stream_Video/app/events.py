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
    Inicializa cámara, detector y arranca el hilo de captura/procesado.
    Optimizado para menor CPU y latencia.
    """

    # =========================
    # ESTADO INICIAL
    # =========================
    state.set_active_camera(None)

    with state.cam_lock:
        state.cam = None

    # =========================
    # DETECTOR
    # =========================
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

        min_body_height=config.MIN_BODY_HEIGHT,
        aspect_ratio_lying=config.ASPECT_RATIO_LYING,
        max_angle_standing=config.MAX_ANGLE_STANDING,
        min_angle_lying=config.MIN_ANGLE_LYING,
        head_tilt_min_standing=config.HEAD_TILT_MIN_STANDING,
        com_y_standing_max=config.COM_Y_STANDING_MAX,
        com_y_sitting_max=config.COM_Y_SITTING_MAX
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
    state.camera_change_event = threading.Event()

    # =========================
    # VARIABLES DE CAÍDA
    # =========================
    prev_pose = None
    prev_pose_ts = None
    confirmar_caida_frames = 0
    CAIDA_CONFIRMADA = False

    # =========================
    # Función para bajar la resolución de la imagen a analizar con IA
    # =========================
    def downscale_for_ai(frame, max_width):
        h, w = frame.shape[:2]

        if w <= max_width:
            return frame  # no escalar si ya es pequeño

        scale = max_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)

        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # =========================
    # THREAD PRINCIPAL
    # =========================
    def capture_loop():
        idle_sleep = 0.03
        active_sleep = 0.01

        while running_event.is_set():

            # 🔁 Cambio de cámara
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

            with state.cam_lock:
                cam = state.cam

            if cam is None:
                time.sleep(idle_sleep)
                continue

            frame = cam.obtener_frame()
            if frame is None:
                time.sleep(idle_sleep)
                continue

            # 📥 Guardar SOLO el último frame
            with state.frame_lock:
                state.latest_raw_frame = frame
                state.last_frame_ts = time.time()

            time.sleep(active_sleep)


    def analysis_loop():
        nonlocal prev_pose, prev_pose_ts, confirmar_caida_frames, CAIDA_CONFIRMADA

        idle_sleep = 0.01
        last_processed_ts = None 

        while running_event.is_set():

            with state.frame_lock:
                frame = state.latest_raw_frame
                frame_ts = state.last_frame_ts

            if frame is None or frame_ts == last_processed_ts:
                time.sleep(idle_sleep)
                continue

            last_processed_ts = frame_ts
            now = time.time()

            # 🧠 Copia SOLO para IA
            frame_for_ai = frame.copy()
            frame_for_ai = downscale_for_ai(frame_for_ai, config.AI_MAX_WIDTH)

            with state.process_lock:
                result = detector.analyze(frame_for_ai)

            present = result.get("present", False)
            persona_real = presence.update(present)

            pose_name = "desconocido"
            draw_needed = False
            frame_out = frame

            # =========================
            # PERSONA DETECTADA
            # =========================
            if persona_real and present:

                pose_name = detector.clasificar_pose(result)
                caida_detectada = False

                if prev_pose and prev_pose_ts:
                    if (
                        prev_pose in ("de_pie", "sentado")
                        and pose_name == "acostado"
                        and (now - prev_pose_ts) < 1.2
                    ):
                        caida_detectada = True

                confirmar_caida_frames = (
                    confirmar_caida_frames + 1 if caida_detectada else 0
                )

                CAIDA_CONFIRMADA = confirmar_caida_frames >= 3

                if pose_name != "desconocido" and not CAIDA_CONFIRMADA:
                    prev_pose = pose_name
                    prev_pose_ts = now

                draw_needed = True

            # =========================
            # NO HAY PERSONA
            # =========================
            else:
                with state.caida_lock:
                    state.caida_activa = False
                    state.caida_ts = None

                prev_pose = None
                prev_pose_ts = None
                confirmar_caida_frames = 0
                CAIDA_CONFIRMADA = False
                draw_needed = True

            # =========================
            # DIBUJO
            # =========================
            if draw_needed:
                frame_out = frame.copy()

                if persona_real and present:
                    if result.get("landmarks") is not None:
                        draw_pose_on_frame(frame_out, result["landmarks"])

                    color = get_pose_color(pose_name)

                    cv2.putText(
                        frame_out,
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
                            frame_out,
                            "!!! CAIDA DETECTADA !!!",
                            (20, 100),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.3,
                            (0, 0, 255),
                            4
                        )
                else:
                    cv2.putText(
                        frame_out,
                        "NO HAY PERSONA",
                        (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (200, 200, 200),
                        2
                    )

            # =========================
            # PUBLICAR
            # =========================
            with state.frame_lock:
                state.current_frame = frame_out
                state.latest_result = {
                    "timestamp": now,
                    "persona_real": persona_real,
                    "present": present,
                    "pose": pose_name,
                    "caida": CAIDA_CONFIRMADA,
                    "visibility_count": result.get("visibility_count"),
                    "body_height": result.get("body_height"),
                    "aspect_ratio": result.get("aspect_ratio"),
                    "angle_from_vertical": result.get("angle_from_vertical"),
                    "center_of_mass_y": result.get("center_of_mass_y"),
                }
                state.latest_result_ts = now

            time.sleep(idle_sleep)



    # =========================
    # ARRANQUE
    # =========================
    t_capture = threading.Thread(target=capture_loop, daemon=True)
    t_analysis = threading.Thread(target=analysis_loop, daemon=True)

    t_capture.start()
    t_analysis.start()

    try:
        yield
    finally:
        running_event.clear()
        time.sleep(0.2)
        with state.cam_lock:
            if state.cam:
                state.cam.liberar()
