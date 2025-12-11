import mediapipe as mp
import numpy as np
import cv2
import math


class PersonDetector:

    def __init__(
        self,
        min_detection_conf=0.7,
        min_tracking_conf=0.7,
        vis_thresh=0.7,
        min_visible_landmarks=10,
        hombros_min_px=40,
        hombros_max_px=1000,
        dibujar=False
    ):
        self.vis_thresh = vis_thresh
        self.min_visible_landmarks = min_visible_landmarks
        self.hombros_min_px = hombros_min_px
        self.hombros_max_px = hombros_max_px
        self.dibujar = dibujar

        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=min_detection_conf,
            min_tracking_confidence=min_tracking_conf,
            model_complexity=1,
            enable_segmentation=False
        )

        self.LM = mp.solutions.pose.PoseLandmark

        self.LANDMARKS_CLAVE = [
            self.LM.NOSE,
            self.LM.LEFT_SHOULDER,
            self.LM.RIGHT_SHOULDER,
            self.LM.LEFT_ELBOW,
            self.LM.RIGHT_ELBOW,
            self.LM.LEFT_HIP,
            self.LM.RIGHT_HIP,
            self.LM.LEFT_KNEE,
            self.LM.RIGHT_KNEE
        ]

    # ---------------------------------------------------------------------
    # MÉTODO PRINCIPAL: analiza un frame
    # ---------------------------------------------------------------------
    def analyze(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if not results.pose_landmarks:
            return {
                "present": False,
                "landmarks": None
            }

        lm = results.pose_landmarks
        vis_count = sum(1 for p in lm.landmark if p.visibility >= self.vis_thresh)

        present = vis_count >= self.min_visible_landmarks

        shoulder_px = None
        angle_torso = None
        head_tilt = None

        try:
            ls = lm.landmark[self.LM.LEFT_SHOULDER]
            rs = lm.landmark[self.LM.RIGHT_SHOULDER]
            lx = int(ls.x * w)
            rx = int(rs.x * w)
            shoulder_px = abs(rx - lx)
        except:
            pass

        try:
            lhip = lm.landmark[self.LM.LEFT_HIP]
            rhip = lm.landmark[self.LM.RIGHT_HIP]
            mx = (lhip.x + rhip.x) / 2
            my = (lhip.y + rhip.y) / 2
            cy_x = (mx * w)
            cy_y = (my * h)

            nose = lm.landmark[self.LM.NOSE]
            nx = (nose.x * w)
            ny = (nose.y * h)

            angle_torso = math.degrees(math.atan2(ny - cy_y, nx - cy_x))
        except:
            pass

        try:
            nose = lm.landmark[self.LM.NOSE]
            lhip = lm.landmark[self.LM.LEFT_HIP]
            rhip = lm.landmark[self.LM.RIGHT_HIP]
            hip_y = (lhip.y + rhip.y) / 2
            head_tilt = hip_y - nose.y
        except:
            pass

        if self.dibujar:
            mp.solutions.drawing_utils.draw_landmarks(
                frame,
                lm,
                mp.solutions.pose.POSE_CONNECTIONS,
                mp.solutions.drawing_utils.DrawingSpec(thickness=2, circle_radius=2),
                mp.solutions.drawing_utils.DrawingSpec(thickness=2)
            )

        return {
            "present": present,
            "visibility_count": vis_count,
            "shoulder_px": shoulder_px,
            "angle_torso_deg": angle_torso,
            "head_tilt": head_tilt,
            "landmarks": lm
        }

    # ---------------------------------------------------------------------
    # CLASIFICACIÓN DE POSE
    # img_w y img_h ahora son opcionales → evita el error del servidor
    # ---------------------------------------------------------------------
    def clasificar_pose(self, landmarks, img_w=None, img_h=None):
        """
        Clasificación de pose simple pero más robusta.

        Lógica combinada:
        - usa posiciones normalizadas (y relativas) de nariz/hombros/caderas
        - calcula un 'ángulo vertical' basado en el vector nariz->caderas
        - aplica rules con umbrales conservadores
        - si se pasan img_w/img_h puede usar comparaciones en píxeles (opcional)
        """
        try:
            lm = landmarks.landmark
            nose = lm[self.LM.NOSE]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
        except Exception:
            return "desconocido"

        # centroides normalizados (0..1)
        shoulder_y = (ls.y + rs.y) / 2.0
        hip_y = (lhip.y + rhip.y) / 2.0
        nose_y = nose.y

        # torso_height en coordenadas normalizadas (evita división por 0)
        torso_height = max(1e-6, abs(shoulder_y - hip_y))

        # ANGULO VERTICAL: nariz -> cadera media (0° vertical, 90° horizontal)
        hip_mid_x = (lhip.x + rhip.x) / 2.0
        hip_mid_y = hip_y
        dx = hip_mid_x - nose.x
        dy = hip_mid_y - nose.y
        angle_deg = math.degrees(math.atan2(abs(dx), abs(dy) + 1e-9))  # 0 vertical, 90 horizontal

        # HEAD TILT (normalizado por anchura de hombros)
        shoulders_width = max(1e-6, abs(ls.x - rs.x))
        head_tilt = abs(nose.x - (ls.x + rs.x) / 2.0) / shoulders_width

        # Si se proporcionan dimensiones, también calcular algunas métricas en píxeles (opcional)
        if img_w and img_h:
            shoulder_px = math.hypot((ls.x - rs.x) * img_w, (ls.y - rs.y) * img_h)
            nose_hip_px = abs((nose_y - hip_y) * img_h)
        else:
            shoulder_px = None
            nose_hip_px = None

        # ---------- Reglas (ordenadas por prioridad) ----------

        # 1) CAIDO: cuerpo muy horizontal (ángulo grande) O nariz muy cerca verticalmente de cadera
        if angle_deg >= 65 or (nose_hip_px is not None and nose_hip_px < 0.06 * (img_h if img_h else 1)):
            return "caido"

        # 2) DE PIE: nariz arriba de hombros y hombros por encima de cadera y ángulo pequeño
        #    - usamos combinación: posición relativa + ángulo < umbral
        if (nose_y < shoulder_y and shoulder_y < hip_y) and (angle_deg <= 25):
            return "de_pie"

        # 3) SENTADO: hombros no muy separados verticalmente de cadera (torso reducido)
        #    o ángulo intermedio (no horizontal ni vertical total)
        if abs(shoulder_y - hip_y) <= 0.14 or (25 < angle_deg < 50):
            # extra: si rodillas están muy abajo respecto a cadera, reforzamos sentado
            try:
                lk = lm[self.LM.LEFT_KNEE]
                rk = lm[self.LM.RIGHT_KNEE]
                knee_y = (lk.y + rk.y) / 2.0
                knee_hip_rel = (hip_y - knee_y) / torso_height
                if knee_hip_rel < 0.6:  # rodillas relativamente altas -> sentado
                    return "sentado"
            except Exception:
                # sin info de rodillas, fallback a regla previa
                return "sentado"
            return "sentado"

        # 4) DORMIDO: postura tipo sentado/semicombinada pero con cabeza ladeada
        if (25 < angle_deg < 50) and (head_tilt > 0.25):
            return "dormido"

        # 5) Si no coincide nada, devolver "desconocido" (mejor que forzar)
        return "desconocido"
