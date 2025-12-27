import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
import cv2
from core import config
from detectors.person_detector import PersonDetector
from services.camera_service import Camara
from services.person_service import PersonPresenceController
from services.pose_service import draw_pose_on_frame, get_pose_color
from services.video_service import reset_camera_state
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
        model_path=Path(__file__).resolve().parent.parent / "modelo pose" / "pose_model.onnx",
        min_detection_conf=config.DETECTION_CONF,
        min_tracking_conf=config.TRACKING_CONF,
        vis_thresh=config.VIS_THRESH,
        min_visible_landmarks=config.MIN_LANDMARKS,
        model_complexity=config.MODEL_COMPLEXITY,
        enable_segmentation=config.ENABLE_SEGMENTATION,
        smooth_landmarks=config.SMOOTH_LANDMARKS
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
    # Función para reestablecer la configuración
    # =========================
    def reset_camera_state():
        with state.cam_lock:
            if state.cam:
                state.cam.liberar()
            state.cam = None

        with state.frame_lock:
            state.latest_raw_frame = None
            state.last_frame_ts = None

        state.active_rtsp_url = None
        state.camera_dead = False
        state.last_reconnect_ts = 0

    # =========================
    # THREAD STREAMING
    # =========================
    def capture_loop():
        idle_sleep = 0.05
        active_sleep = 0.01

        while running_event.is_set():

            # 🚫 No hay RTSP activo
            if not state.active_rtsp_url:
                time.sleep(0.2)
                continue

            # 🔁 Cambio de cámara / RTSP
            if state.camera_change_event.is_set():
                with state.cam_lock:

                    # 💣 DESTRUIR cámara anterior completamente
                    if state.cam:
                        try:
                            state.cam.liberar()
                        except:
                            pass
                        state.cam = None

                    # 🔄 CREAR objeto nuevo (socket nuevo)
                    state.cam = Camara(
                        state.active_rtsp_url,
                        buffer_size=config.CAP_BUFFERSIZE
                    )

                # 🧼 Limpiar frames y timestamps
                with state.frame_lock:
                    state.latest_raw_frame = None
                    state.last_frame_ts = None

                state.camera_change_event.clear()
                time.sleep(0.3)   # deja que FFmpeg abra bien
                continue

            # 📷 Obtener cámara actual
            with state.cam_lock:
                cam = state.cam

            if cam is None:
                time.sleep(idle_sleep)
                continue

            # 🎞️ Leer frame
            frame = cam.obtener_frame()

            if frame is None:
                time.sleep(idle_sleep)
                continue

            # 📥 Guardar último frame válido
            with state.frame_lock:
                state.latest_raw_frame = frame
                state.last_frame_ts = time.time()

            time.sleep(active_sleep)

    def analysis_loop():
        idle_sleep = 0.005
        last_processed_ts = None

        while running_event.is_set():

            # =========================
            # OBTENER FRAME
            # =========================
            with state.frame_lock:
                frame = state.latest_raw_frame
                frame_ts = state.last_frame_ts

            if frame is None or frame_ts == last_processed_ts:
                time.sleep(idle_sleep)
                continue

            last_processed_ts = frame_ts

            now = time.time()

            # =========================
            # FPS DINÁMICO (GATE)
            # =========================
            min_interval = 1.0 / state.ai_fps
            if now - state.last_ai_ts < min_interval:
                time.sleep(0.001)
                continue

            state.last_ai_ts = now

            # =========================
            # IA (COPIA + DOWNSCALE)
            # =========================
            frame_for_ai = frame.copy()
            frame_for_ai = downscale_for_ai(
                frame_for_ai,
                config.AI_MAX_WIDTH
            )

            t0 = time.time()
            with state.process_lock:
                result = detector.analyze(frame_for_ai)
            t1 = time.time()

            inference_time = t1 - t0

            # =========================
            # EMA + AJUSTE FPS
            # =========================
            alpha = config.AI_SMOOTHING
            state.avg_inference_time = (
                alpha * state.avg_inference_time
                + (1 - alpha) * inference_time
            )

            if state.avg_inference_time > config.AI_TARGET_INFERENCE * 1.2:
                state.ai_fps = max(
                    config.AI_FPS_MIN,
                    state.ai_fps * 0.9
                )

            elif state.avg_inference_time < config.AI_TARGET_INFERENCE * 0.7:
                state.ai_fps = min(
                    config.AI_FPS_MAX,
                    state.ai_fps * 1.05
                )

            # =========================
            # LÓGICA DE PERSONA
            # =========================
            present = result.get("present", False)
            persona_real = presence.update(present)

            pose_name = "desconocido"

            if persona_real and present:
                pose_name = detector.clasificar_pose(result)

            # =========================
            # DIBUJO (COPIA FINAL)
            # =========================
            frame_out = frame.copy()

            if persona_real and present:
                if config.DIBUJAR and result.get("landmarks") is not None:
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
                    "visibility_count": result.get("visibility_count"),
                    "body_height": result.get("body_height"),
                    "aspect_ratio": result.get("aspect_ratio"),
                    "angle_from_vertical": result.get("angle_from_vertical"),
                    "center_of_mass_y": result.get("center_of_mass_y"),
                    "ai_fps": round(state.ai_fps, 2),
                    "ai_latency_ms": int(state.avg_inference_time * 1000),
                }

                state.latest_result_ts = now


    def camera_watchdog_loop():
        reconnect_attempts = 0

        while running_event.is_set():
            time.sleep(0.5)

            # 🚫 No hay RTSP activo → nada que vigilar
            if not state.active_rtsp_url:
                reconnect_attempts = 0
                state.camera_dead = False
                continue

            with state.frame_lock:
                last_ts = state.last_frame_ts

            # 🟡 Nunca hubo frame → NO watchdog
            if last_ts is None:
                continue

            now = time.time()

            # 🛑 Cámara congelada
            if now - last_ts > config.CAMERA_TIMEOUT:

                if now - state.last_reconnect_ts < config.CAMERA_RECONNECT_COOLDOWN:
                    continue

                reconnect_attempts += 1
                state.last_reconnect_ts = now
                state.camera_dead = True

                print("⚠️ Watchdog: cámara congelada, reiniciando")

                with state.cam_lock:
                    if state.cam:
                        state.cam.liberar()
                        state.cam = None   # limpiar referencia

                # 🔁 Reapertura controlada
                state.camera_change_event.set()

                if reconnect_attempts >= config.MAX_RECONNECT_ATTEMPTS:
                    print("❌ Watchdog: demasiados intentos, enfriando")
                    reset_camera_state()
                    reconnect_attempts = 0
                    time.sleep(5)

            else:
                # 🟢 Cámara viva
                reconnect_attempts = 0
                state.camera_dead = False



    # =========================
    # ARRANQUE
    # =========================
    t_capture = threading.Thread(target=capture_loop, daemon=True)
    t_analysis = threading.Thread(target=analysis_loop, daemon=True)
    t_watchdog = threading.Thread(target=camera_watchdog_loop, daemon=True)

    t_capture.start()
    t_analysis.start()
    t_watchdog.start()

    try:
        yield
    finally:
        running_event.clear()
        time.sleep(0.2)
        with state.cam_lock:
            if state.cam:
                state.cam.liberar()
