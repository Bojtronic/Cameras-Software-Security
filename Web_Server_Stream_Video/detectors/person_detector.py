import mediapipe as mp
import numpy as np
import cv2
import math


class PersonDetector:

    def __init__(
        self,
        min_detection_conf=0.5,
        min_tracking_conf=0.5,
        vis_thresh=0.5,
        min_visible_landmarks=4,
        hombros_min_px=10,
        hombros_max_px=1000,
        model_complexity=1,
        enable_segmentation=False,
        smooth_landmarks=True,
        dibujar=False,
        
        
        min_body_height=0.25,
        aspect_ratio_lying=0.9,
        max_angle_standing=20,
        min_angle_lying=60,
        head_tilt_min_standing=0.12,
        com_y_standing_max=0.55,
        com_y_sitting_max=0.75
    ):
        self.vis_thresh = vis_thresh
        self.min_visible_landmarks = min_visible_landmarks
        self.hombros_min_px = hombros_min_px
        self.hombros_max_px = hombros_max_px
        self.dibujar = dibujar
        
        self.min_body_height = min_body_height
        self.aspect_ratio_lying = aspect_ratio_lying
        self.max_angle_standing = max_angle_standing
        self.min_angle_lying = min_angle_lying
        self.head_tilt_min_standing = head_tilt_min_standing
        self.com_y_standing_max = com_y_standing_max
        self.com_y_sitting_max = com_y_sitting_max

        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=min_detection_conf,
            min_tracking_confidence=min_tracking_conf,
            model_complexity=model_complexity,
            enable_segmentation=enable_segmentation,
            smooth_landmarks=smooth_landmarks
        )

        self.LM = mp.solutions.pose.PoseLandmark

    def _has_landmarks(self, lm, *ids):
        """
        Verifica que todos los landmarks indicados:
        - Existan
        - Tengan visibilidad >= vis_thresh
        """
        return all(
            lm[i].visibility >= self.vis_thresh
            for i in ids
        )

    # ---------------------------------------------------------------------
    # MÉTODO PRINCIPAL: analiza un frame
    # ---------------------------------------------------------------------
    def analyze(self, frame):
        """
        Objetivo:
        - Detectar presencia humana real
        - Extraer geometría corporal robusta
        - Permitir clasificación fiable:
            * de_pie
            * sentado
            * acostado (pose NO permitida)
        """

        # -------------------------------------------------
        # 1️⃣ Preprocesamiento
        # -------------------------------------------------
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        # Si MediaPipe no detecta pose → no hay persona
        if not results.pose_landmarks:
            return {
                "present": False,
                "landmarks": None
            }

        lm = results.pose_landmarks.landmark

        # -------------------------------------------------
        # 2️⃣ Visibilidad y presencia humana
        # -------------------------------------------------
        # Conteo de landmarks suficientemente visibles
        vis_count = sum(p.visibility >= self.vis_thresh for p in lm)

        # Presencia estricta:
        # - suficientes landmarks visibles
        # - estructura humana válida
        """
        present = (
            vis_count >= self.min_visible_landmarks
            and self._es_pose_valida(lm)
        )
        """
        present = vis_count >= self.min_visible_landmarks

        # -------------------------------------------------
        # 3️⃣ Extracción segura de landmarks clave
        # -------------------------------------------------
        try:
            nose = lm[self.LM.NOSE]
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
            lk = lm[self.LM.LEFT_KNEE]
            rk = lm[self.LM.RIGHT_KNEE]
        except Exception:
            # Algo raro → descartar frame
            return {
                "present": False,
                "landmarks": None
            }

        # -------------------------------------------------
        # 4️⃣ Geometría corporal básica
        # -------------------------------------------------

        # Ancho de hombros (en píxeles)
        shoulder_px = abs(int((rs.x - ls.x) * w))

        # Ancho de caderas (normalizado)
        hip_width = abs(lhip.x - rhip.x)

        # Alturas normalizadas
        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2
        knee_y = (lk.y + rk.y) / 2
        nose_y = nose.y

        # Altura corporal aproximada
        body_height = abs(knee_y - nose_y)

        # Relación ancho / alto (clave para "acostado")
        aspect_ratio = abs(ls.x - rs.x) / max(body_height, 1e-6)

        # -------------------------------------------------
        # 5️⃣ Orientación del torso
        # -------------------------------------------------
        cx = ((lhip.x + rhip.x) / 2) * w
        cy = ((lhip.y + rhip.y) / 2) * h
        nx = nose.x * w
        ny = nose.y * h

        # Ángulo absoluto del torso
        angle_torso_deg = math.degrees(math.atan2(ny - cy, nx - cx))

        # Ángulo respecto a la vertical (más interpretable)
        angle_from_vertical = abs(90 - abs(angle_torso_deg))

        # Inclinación cabeza–cadera (normalizada)
        head_tilt = hip_y - nose_y

        # -------------------------------------------------
        # 6️⃣ Centro de masa aproximado (barato y útil)
        # -------------------------------------------------
        center_of_mass_y = (nose_y + shoulder_y + hip_y) / 3

        # -------------------------------------------------
        # 7️⃣ Dibujo opcional
        # -------------------------------------------------
        if self.dibujar:
            mp.solutions.drawing_utils.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp.solutions.pose.POSE_CONNECTIONS,
                mp.solutions.drawing_utils.DrawingSpec(thickness=2, circle_radius=2),
                mp.solutions.drawing_utils.DrawingSpec(thickness=2)
            )

        # -------------------------------------------------
        # 8️⃣ Resultado final
        # -------------------------------------------------
        return {
            "present": present,
            "visibility_count": vis_count,

            # Geometría
            "shoulder_px": shoulder_px,
            "hip_width": hip_width,
            "body_height": body_height,
            "aspect_ratio": aspect_ratio,

            # Orientación
            "angle_torso_deg": angle_torso_deg,
            "angle_from_vertical": angle_from_vertical,
            "head_tilt": head_tilt,

            # Posición global
            "center_of_mass_y": center_of_mass_y,

            # Landmarks crudos (solo para clasificación / debug)
            "landmarks": results.pose_landmarks
        }


    # ---------------------------------------------------------------------
    # CLASIFICACIÓN DE POSE
    # ---------------------------------------------------------------------
    def clasificar_pose(self, data):
        """
        Clasifica la pose usando features extraídas en analyze()

        Retorna:
            "de_pie"
            "sentado"
            "acostado"
            "desconocido"
        """

        if not data or not data.get("present", False):
            return "desconocido"

        # ----------------------------
        # Extraer features
        # ----------------------------
        body_height = data["body_height"]
        aspect_ratio = data["aspect_ratio"]
        angle_from_vertical = data["angle_from_vertical"]
        head_tilt = data["head_tilt"]
        com_y = data["center_of_mass_y"]

        # ----------------------------
        # Filtrado básico (ruido)
        # ----------------------------
        if body_height < self.min_body_height:
            return "desconocido"

        # ----------------------------
        # 1️⃣ ACOSTADO (CRÍTICO)
        # ----------------------------
        # Persona casi horizontal o muy ancha respecto a su altura
        if (
            aspect_ratio > self.aspect_ratio_lying
            or angle_from_vertical > self.min_angle_lying
        ):
            return "acostado"

        # ----------------------------
        # 2️⃣ DE PIE
        # ----------------------------
        if (
            angle_from_vertical < self.max_angle_standing
            and head_tilt > self.head_tilt_min_standing
            and com_y < self.com_y_standing_max
        ):
            return "de_pie"

        # ----------------------------
        # 3️⃣ SENTADO
        # ----------------------------
        if (
            angle_from_vertical < self.max_angle_standing
            and self.com_y_standing_max <= com_y <= self.com_y_sitting_max
        ):
            return "sentado"

        return "desconocido"



    def _es_pose_valida(self, lm):
        """
        Validación estructural mínima de cuerpo humano.
        NO clasifica pose.
        SOLO filtra detecciones imposibles o ruido.
        """

        try:
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
        except Exception:
            return False

        # ----------------------------------
        # 1️⃣ Visibilidad mínima en estructura
        # ----------------------------------
        if (
            ls.visibility < self.vis_thresh or
            rs.visibility < self.vis_thresh or
            lhip.visibility < self.vis_thresh or
            rhip.visibility < self.vis_thresh
        ):
            return False

        # ----------------------------------
        # 2️⃣ Orden anatómico vertical
        # ----------------------------------
        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2

        if hip_y <= shoulder_y: # ¿que pasa si está de cabeza o si la persona cae y en el video la cadera queda arriba y los hombros abajo?
            return False

        # ----------------------------------
        # 3️⃣ Tamaño mínimo de persona
        # ----------------------------------
        shoulder_width = abs(ls.x - rs.x)

        if shoulder_width < self.hombros_min_px: 
            return False

        return True

