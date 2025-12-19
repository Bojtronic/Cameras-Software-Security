import mediapipe as mp
import numpy as np
import cv2
import math


class PersonDetector:

    def __init__(
        self,
        min_detection_conf=0.6,
        min_tracking_conf=0.6,
        vis_thresh=0.6,
        min_visible_landmarks=6,
        hombros_min_px=30,
        hombros_max_px=600,
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
            #model_complexity=1,
            model_complexity = 2,
            enable_segmentation=False
        )

        self.LM = mp.solutions.pose.PoseLandmark

        """
        self.LANDMARKS_CLAVE = [
            self.LM.LEFT_SHOULDER,
            self.LM.RIGHT_SHOULDER,
            #self.LM.LEFT_ELBOW,
            #self.LM.RIGHT_ELBOW,
            self.LM.LEFT_HIP,
            self.LM.RIGHT_HIP,
            #self.LM.LEFT_KNEE,
            #self.LM.RIGHT_KNEE
        ]
        """

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
        """
        vis_count = sum(
            1 for idx in self.LANDMARKS_CLAVE
            if lm.landmark[idx].visibility >= self.vis_thresh
        )
        """

        present = (
            vis_count >= self.min_visible_landmarks
            and self._es_pose_valida(lm.landmark)
        )

        #present = vis_count >= self.min_visible_landmarks

        shoulder_px = None
        angle_torso = None
        head_tilt = None

        try:
            ls = lm.landmark[self.LM.LEFT_SHOULDER]
            rs = lm.landmark[self.LM.RIGHT_SHOULDER]
            lx = int(ls.x * w)
            rx = int(rs.x * w)
            shoulder_px = abs(rx - lx)
        except Exception:
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
        except Exception:
            pass

        try:
            nose = lm.landmark[self.LM.NOSE]
            lhip = lm.landmark[self.LM.LEFT_HIP]
            rhip = lm.landmark[self.LM.RIGHT_HIP]
            hip_y = (lhip.y + rhip.y) / 2
            head_tilt = hip_y - nose.y
        except Exception:
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
    # img_w y img_h son opcionales
    # ---------------------------------------------------------------------
    def clasificar_pose(self, landmarks, img_w=None, img_h=None):
        try:
            lm = landmarks.landmark
            nose = lm[self.LM.NOSE]
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
            lk = lm[self.LM.LEFT_KNEE]
            rk = lm[self.LM.RIGHT_KNEE]
        except Exception:
            return "desconocido"

        # Coordenadas normalizadas
        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2
        knee_y = (lk.y + rk.y) / 2
        nose_y = nose.y

        torso_height = max(1e-6, abs(hip_y - shoulder_y))
        body_height = abs(knee_y - nose_y)
        shoulder_width = abs(ls.x - rs.x)

        # Relación ancho / alto → clave para acostado
        aspect_ratio = shoulder_width / max(body_height, 1e-6)

        # -----------------------------
        # 1️⃣ ACOSTADO (CRÍTICO)
        # -----------------------------
        if aspect_ratio > 0.9 or abs(nose_y - hip_y) < torso_height * 0.3:
            return "acostado"

        # -----------------------------
        # 2️⃣ DE PIE
        # -----------------------------
        if nose_y < shoulder_y < hip_y < knee_y:
            return "de_pie"

        # -----------------------------
        # 3️⃣ SENTADO
        # -----------------------------
        if hip_y < knee_y and abs(hip_y - knee_y) < torso_height * 0.7:
            return "sentado"

        return "desconocido"


    def _es_pose_valida(self, lm):
        try:
            nose = lm[self.LM.NOSE]
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
        except Exception:
            return False

        # Visibilidad estructural mínima
        #required = [nose, ls, rs, lhip, rhip]
        required = [ls, rs, lhip, rhip]
        if any(p.visibility < self.vis_thresh for p in required):
            return False

        # Proporciones humanas básicas
        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2

        if hip_y <= shoulder_y:  # caderas arriba de hombros → imposible
            return False

        torso_height = abs(hip_y - shoulder_y)
        head_height = abs(nose.y - shoulder_y)

        if torso_height < head_height * 0.8:
            return False

        shoulder_width = abs(ls.x - rs.x)
        if shoulder_width < 0.05:  # persona demasiado pequeña → ruido
            return False

        return True
