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
        # =========================================================
        # 1️⃣ PREPROCESAMIENTO DE IMAGEN
        # =========================================================
        # MediaPipe trabaja en RGB, OpenCV usa BGR,
        # por eso convertimos el espacio de color.
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Ejecuta el modelo de pose
        results = self.pose.process(rgb)

        # Si MediaPipe no detecta un esqueleto, no hay persona
        if not results.pose_landmarks:
            return {"present": False, "landmarks": None}

        # Acceso rápido a la lista de landmarks
        lm = results.pose_landmarks.landmark

        # =========================================================
        # 2️⃣ ÁNGULOS DE RODILLAS (flexión de piernas)
        # =========================================================
        # Se calcula el ángulo geométrico:
        #   cadera → rodilla → tobillo
        #
        # Matemáticamente:
        #   cos(θ) = (BA · BC) / (|BA| |BC|)
        #
        # Físicamente:
        #   180° = pierna recta
        #    90° = pierna doblada (sentado)
        #
        # Desde cámara cenital es ruidoso, se usa como apoyo.
        left_knee_angle = self.angle(lm[23], lm[25], lm[27])
        right_knee_angle = self.angle(lm[24], lm[26], lm[28])
        knee_angle = (left_knee_angle + right_knee_angle) / 2

        # =========================================================
        # 3️⃣ LÍNEA CORPORAL (colinealidad)
        # =========================================================
        # Se mide si hombro, cadera y pie están alineados.
        # Si el cuerpo está estirado → ángulo cercano a 180°
        # Si está doblado → ángulo menor.
        left_body_line = self.angle(lm[11], lm[23], lm[27])
        right_body_line = self.angle(lm[12], lm[24], lm[28])
        body_line_angle = (left_body_line + right_body_line) / 2

        # =========================================================
        # 4️⃣ VISIBILIDAD GLOBAL
        # =========================================================
        # MediaPipe asigna a cada punto una visibilidad ∈ [0,1]
        # Contamos cuántos landmarks superan el umbral
        # para saber si la persona es real y completa.
        vis_count = sum(p.visibility >= self.vis_thresh for p in lm)
        present = vis_count >= self.min_visible_landmarks

        # =========================================================
        # 5️⃣ LANDMARKS CLAVE
        # =========================================================
        # Extraemos las partes estructurales del cuerpo
        # que se usan para geometría y proyecciones físicas.
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

        # =========================================================
        # 6️⃣ GEOMETRÍA DEL CUERPO
        # =========================================================

        # Distancia real entre hombros en píxeles:
        # se usa como filtro de tamaño humano
        shoulder_px = abs(int((rs.x - ls.x) * w))

        # Ancho de caderas en coordenadas normalizadas
        hip_width = abs(lhip.x - rhip.x)

        # Promedios verticales de hombros, caderas y rodillas
        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lhip.y + rhip.y) / 2
        knee_y = (lk.y + rk.y) / 2
        nose_y = nose.y

        # Altura corporal proyectada:
        # nariz → rodillas
        # Desde arriba, esta altura cae cuando alguien se acuesta.
        body_height = abs(knee_y - nose_y)

        # =========================================================
        # 7️⃣ ASPECT RATIO (ancho / alto)
        # =========================================================
        # Se calcula como:
        #
        #   ancho del cuerpo (hombros)
        #   --------------------------
        #   altura del cuerpo (nariz→rodillas)
        #
        # Físicamente:
        #   - De pie → valor bajo (alto > ancho)
        #   - Acostado → valor alto (ancho ≈ alto)
        #
        aspect_ratio = abs(ls.x - rs.x) / max(body_height, 1e-6)

        # =========================================================
        # 8️⃣ CENTRO DE MASA
        # =========================================================
        # Aproximación del centro del cuerpo
        # promediando cabeza, hombros y caderas.
        #
        # Desde cámara cenital:
        #   - persona de pie → masa arriba
        #   - persona acostada → masa baja
        #
        center_of_mass_y = (nose_y + shoulder_y + hip_y) / 3

        # =========================================================
        # 9️⃣ ORIENTACIÓN DEL TORSO
        # =========================================================
        # Vector desde caderas → nariz
        # indica la orientación principal del cuerpo.
        cx = ((lhip.x + rhip.x) / 2) * w
        cy = ((lhip.y + rhip.y) / 2) * h
        nx = nose.x * w
        ny = nose.y * h

        angle_torso_deg = math.degrees(math.atan2(ny - cy, nx - cx))

        # Distancia angular respecto a la vertical
        # (más útil en cámaras laterales que cenitales)
        angle_from_vertical = abs(90 - abs(angle_torso_deg))

        # Diferencia vertical cabeza ↔ caderas
        # grande = cuerpo vertical
        # pequeño = cuerpo horizontal
        head_tilt = hip_y - nose_y

        # =========================================================
        # 10️⃣ TORSO SPREAD (MÉTRICA MÁS IMPORTANTE)
        # =========================================================
        # Proyección real del cuerpo sobre el suelo.
        # Distancia entre:
        #   centro de hombros ↔ centro de caderas
        #
        # De pie → pequeño
        # Sentado → medio
        # Acostado → grande
        #
        sx = (ls.x + rs.x) / 2
        sy = (ls.y + rs.y) / 2

        hx = (lhip.x + rhip.x) / 2
        hy = (lhip.y + rhip.y) / 2

        # Distancia euclidiana en el plano de la imagen
        torso_spread = math.hypot(sx - hx, sy - hy)

        # =========================================================
        # 11️⃣ SALIDA
        # =========================================================
        # Se devuelven todas las métricas físicas
        # para clasificación y depuración.
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

        # ==========================================================
        # 0️⃣ VALIDACIÓN
        # ==========================================================
        if not data or not data.get("present", False):
            return "desconocido"

        # ==========================================================
        # 1️⃣ VARIABLES GEOMÉTRICAS
        # ==========================================================
        h         = data["body_height"]
        ar        = data["aspect_ratio"]
        spread    = data["torso_spread"]
        knee      = data["knee_angle"]
        body_line = data["body_line_angle"]
        head_tilt = data["head_tilt"]

        # ==========================================================
        # 2️⃣ FILTRO DE RUIDO
        # ==========================================================
        if h < self.min_body_height:
            return "desconocido"

        # ==========================================================
        # 3️⃣ SISTEMA DE VOTACIÓN
        # ==========================================================
        score_standing = 0
        score_sitting  = 0
        score_lying    = 0

        # ==========================================================
        # 🔥 ACOSTADO POR ORIENTACIÓN GLOBAL (caída real)
        # ==========================================================
        # Si el cuerpo está casi horizontal en la imagen,
        # significa que la persona está en el suelo,
        # sin importar tamaño, distancia o perspectiva.
        if 70 < body_line < 110:
            score_lying    += 8
            score_standing -= 5
            score_sitting  -= 3
    
        # ==========================================================
        # 🔥 4️⃣ ACOSTADO ABSOLUTO (expandido en el suelo)
        # ==========================================================
        # Cuerpo muy ancho y separado → acostado transversal
        if spread > 0.17 and ar > 1.0:
            score_lying    += 6
            score_standing -= 4
            score_sitting  -= 2

        # ==========================================================
        # 🔥 5️⃣ ACOSTADO LONGITUDINAL (alineado con la cámara)
        # ==========================================================
        # Muy largo y recto aunque no sea ancho → acostado
        if spread > 0.20 and body_line > 140:
            score_lying    += 5
            score_standing -= 3
            score_sitting  -= 2

        # ==========================================================
        # 🔥 6️⃣ SENTADO FUERTE
        # ==========================================================
        if knee < 135:
            score_sitting  += 4
            score_standing -= 3

        # ==========================================================
        # 7️⃣ TORSO_SPREAD (métrica base)
        # ==========================================================
        # En tu cámara:
        #   - spread pequeño → de pie
        #   - spread medio   → sentado
        #   - spread grande  → acostado
        if spread > 0.14:
            score_lying += 3
        elif spread > 0.12:
            score_sitting += 2
        else:
            score_standing += 3

        # ==========================================================
        # 8️⃣ ASPECT_RATIO
        # ==========================================================
        # Acostado longitudinal → cuerpo estrecho pero largo
        if ar < 0.5 and spread > 0.18:
            score_lying += 3
        elif ar > 0.5:
            score_sitting += 2
        else:
            score_standing += 2

        # ==========================================================
        # 9️⃣ BODY_LINE
        # ==========================================================
        # Recto + torso largo = acostado
        # Recto + torso corto = de pie
        # Doblado = sentado
        if body_line > 140:
            if spread > 0.16:
                score_lying += 3
            else:
                score_standing += 2
        else:
            score_sitting += 3

        # ==========================================================
        # 🔟 PIERNAS
        # ==========================================================
        if knee < 120:
            score_sitting += 3
        elif knee > 160 and spread < 0.15:
            score_standing += 2

        # ==========================================================
        # 1️⃣1️⃣ DECISIÓN FINAL
        # ==========================================================
        scores = {
            "de pie": score_standing,
            "sentado": score_sitting,
            "acostado": score_lying
        }

        pose = max(scores, key=scores.get)

        # ==========================================================
        # 1️⃣2️⃣ CONTROL DE CONFIANZA
        # ==========================================================
        if scores[pose] < 3:
            return "desconocido"

        return pose


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
