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
        
        min_body_height=0.25,
        aspect_ratio_lying=0.9,
        max_angle_standing=20,
        min_angle_lying=60,
        head_tilt_min_standing=0.12,
        com_y_standing_max=0.55,
        com_y_sitting_max=0.75,
        
        torso_expand_min_lying=0.9,     # equivalente a aspect_ratio_lying
        com_y_lying_min=0.60,          # centro de masa bajo = cuerpo en el suelo
        knee_angle_sitting_max=120,    # debajo de esto es sentado
        knee_angle_standing_min=150,   # encima de esto es de pie
        
        torso_spread_lying=0.10,
        body_line_angle=150
    ):
        self.vis_thresh = vis_thresh
        self.min_visible_landmarks = min_visible_landmarks
        self.hombros_min_px = hombros_min_px
        self.hombros_max_px = hombros_max_px
        
        self.min_body_height = min_body_height
        self.aspect_ratio_lying = aspect_ratio_lying
        self.max_angle_standing = max_angle_standing
        self.min_angle_lying = min_angle_lying
        self.head_tilt_min_standing = head_tilt_min_standing
        self.com_y_standing_max = com_y_standing_max
        self.com_y_sitting_max = com_y_sitting_max
        
        self.torso_expand_min_lying = torso_expand_min_lying
        self.com_y_lying_min = com_y_lying_min
        self.knee_angle_sitting_max = knee_angle_sitting_max
        self.knee_angle_standing_min = knee_angle_standing_min
        
        self.torso_spread_lying = torso_spread_lying
        self.body_line_angle = body_line_angle

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
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if not results.pose_landmarks:
            return {"present": False, "landmarks": None}

        lm = results.pose_landmarks.landmark

        # ============================
        # Rodillas
        # ============================
        left_knee_angle = self.angle(lm[23], lm[25], lm[27])
        right_knee_angle = self.angle(lm[24], lm[26], lm[28])
        knee_angle = (left_knee_angle + right_knee_angle) / 2

        # ============================
        # Línea corporal (colinealidad)
        # ============================
        left_body_line = self.angle(lm[11], lm[23], lm[27])
        right_body_line = self.angle(lm[12], lm[24], lm[28])
        body_line_angle = (left_body_line + right_body_line) / 2

        # ============================
        # Visibilidad
        # ============================
        vis_count = sum(p.visibility >= self.vis_thresh for p in lm)
        present = vis_count >= self.min_visible_landmarks

        try:
            nose = lm[self.LM.NOSE]
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
            lk = lm[self.LM.LEFT_KNEE]
            rk = lm[self.LM.RIGHT_KNEE]
        except:
            return {"present": False, "landmarks": None}

        # ============================
        # Geometría
        # ============================
        shoulder_px = abs(int((rs.x - ls.x) * w))
        hip_width = abs(lhip.x - rhip.x)

        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2
        knee_y = (lk.y + rk.y) / 2
        nose_y = nose.y

        body_height = abs(knee_y - nose_y)

        aspect_ratio = abs(ls.x - rs.x) / max(body_height, 1e-6)

        # ============================
        # Centro de masa
        # ============================
        center_of_mass_y = (nose_y + shoulder_y + hip_y) / 3

        # ============================
        # Ángulo del torso
        # ============================
        cx = ((lhip.x + rhip.x) / 2) * w
        cy = ((lhip.y + rhip.y) / 2) * h
        nx = nose.x * w
        ny = nose.y * h

        angle_torso_deg = math.degrees(math.atan2(ny - cy, nx - cx))
        angle_from_vertical = abs(90 - abs(angle_torso_deg))

        head_tilt = hip_y - nose_y

        # ============================
        # 🔥 MÉTRICA CLAVE PARA ACOSTADO
        # ============================
        # Centro de hombros
        sx = (ls.x + rs.x) / 2
        sy = (ls.y + rs.y) / 2

        # Centro de caderas
        hx = (lhip.x + rhip.x) / 2
        hy = (lhip.y + rhip.y) / 2

        # Distancia normalizada hombros ↔ caderas
        torso_spread = math.hypot(sx - hx, sy - hy)

        # ============================
        # Resultado
        # ============================
        return {
            "present": present,
            "visibility_count": vis_count,

            "shoulder_px": shoulder_px,
            "hip_width": hip_width,
            "body_height": body_height,
            "aspect_ratio": aspect_ratio,
            "torso_spread": torso_spread,

            "angle_torso_deg": angle_torso_deg,
            "angle_from_vertical": angle_from_vertical,
            "knee_angle": knee_angle,
            "body_line_angle": body_line_angle,
            "head_tilt": head_tilt,

            "center_of_mass_y": center_of_mass_y,
            "landmarks": results.pose_landmarks
        }
        
    
    # ---------------------------------------------------------------------
    # CLASIFICACIÓN DE POSE
    # ---------------------------------------------------------------------
    def clasificar_pose(self, data):

        if not data or not data.get("present", False):
            return "desconocido"

        h = data["body_height"]
        ar = data["aspect_ratio"]              # ancho total / alto
        com = data["center_of_mass_y"]         # centro de masa vertical
        knee = data.get("knee_angle", 180)     # ángulo medio de rodillas
        spread = data["torso_spread"]          # hombros ↔ caderas
        body_line = data["body_line_angle"]    # colinealidad hombros-cadera-pies
        angle_from_vertical = data["angle_from_vertical"]

        # ----------------------------
        # Filtro mínimo de tamaño
        # ----------------------------
        if h < self.min_body_height:
            return "desconocido"

        # =====================================================
        # 1️⃣ ACOSTADO (MÁXIMA PRIORIDAD)
        # =====================================================
        # La persona puede estar:
        #   - de lado
        #   - boca arriba
        #   - boca abajo
        #   - con piernas dobladas
        #
        # Por eso usamos:
        #   - aspect_ratio (ocupa ancho)
        #   - torso_spread (cuerpo expandido)
        #   - body_line (estructura alineada)
        #   - centro de masa bajo
        #
        if (
            (
                ar >= self.aspect_ratio_lying
                or spread >= self.torso_spread_lying
            )
            and body_line >= self.body_line_angle
            and com >= self.com_y_lying_min
        ):
            return "acostado"

        # =====================================================
        # 2️⃣ SENTADO
        # =====================================================
        # Rodillas dobladas + cuerpo no expandido
        if (
            knee <= self.knee_angle_sitting_max
            and com <= self.com_y_sitting_max
            and ar < self.aspect_ratio_lying
            and spread < self.torso_spread_lying
        ):
            return "sentado"

        # =====================================================
        # 3️⃣ DE PIE
        # =====================================================
        # Piernas rectas + cuerpo compacto + vertical
        if (
            knee >= self.knee_angle_standing_min
            and ar < self.aspect_ratio_lying * 0.8
            and spread < self.torso_spread_lying * 0.6
            and angle_from_vertical <= self.max_angle_standing
            and com < self.com_y_standing_max
        ):
            return "de pie"

        return "desconocido"


    def angle(self, a, b, c):
        # ángulo ABC en grados
        ba = np.array([a.x - b.x, a.y - b.y])
        bc = np.array([c.x - b.x, c.y - b.y])
        cosang = np.dot(ba, bc) / (np.linalg.norm(ba)*np.linalg.norm(bc) + 1e-6)
        return np.degrees(np.arccos(np.clip(cosang, -1, 1)))





















    def _es_pose_valida(self, lm):
        """
        Validación estructural mínima para cámara cenital (desde el techo).

        Acepta:
        - Personas de pie
        - Personas sentadas
        - Personas caídas o acostadas

        Rechaza:
        - Reflejos
        - Sombras
        - Objetos
        - Fragmentos de cuerpo
        """

        try:
            ls = lm[self.LM.LEFT_SHOULDER]
            rs = lm[self.LM.RIGHT_SHOULDER]
            lhip = lm[self.LM.LEFT_HIP]
            rhip = lm[self.LM.RIGHT_HIP]
        except Exception:
            return False

        # -------------------------------
        # 1️⃣ Visibilidad mínima
        # -------------------------------
        if (
            ls.visibility < self.vis_thresh or
            rs.visibility < self.vis_thresh or
            lhip.visibility < self.vis_thresh or
            rhip.visibility < self.vis_thresh
        ):
            return False

        # -------------------------------
        # 2️⃣ Ancho mínimo de hombros
        # -------------------------------
        shoulder_width = abs(ls.x - rs.x)

        if shoulder_width < self.hombros_min_px:
            return False

        # -------------------------------
        # 3️⃣ Centro de hombros y caderas
        # -------------------------------
        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2

        shoulder_x = (ls.x + rs.x) / 2
        hip_x = (lhip.x + rhip.x) / 2

        # -------------------------------
        # 4️⃣ Distancia hombros ↔ cadera
        # (clave para vista desde arriba)
        # -------------------------------
        torso_dist = math.hypot(shoulder_x - hip_x, shoulder_y - hip_y)

        # Si es extremadamente pequeño → ruido o mala detección
        if torso_dist < 0.02:
            return False

        # Si es extremadamente grande → dos personas mezcladas o error
        if torso_dist > 0.6:
            return False

        # -------------------------------
        # 5️⃣ Relación hombros ↔ cadera
        # Forma humana aproximada
        # -------------------------------
        # Si hombros y caderas están demasiado separados lateralmente
        hip_width = abs(lhip.x - rhip.x)

        if hip_width < 0.01:
            return False

        ratio = shoulder_width / hip_width

        # Valores humanos típicos ~0.6 a ~1.8
        if ratio < 0.4 or ratio > 2.5:
            return False

        # --------------------------------
        # Es una persona válida
        # (de pie, sentada o caída)
        # --------------------------------
        return True
