import mediapipe as mp
import numpy as np
import cv2
import math
import tensorflow as tf
import os
import sys
from pathlib import Path

class PersonDetector:

    def __init__(
        self,
        model_path=None,
        min_detection_conf=0.5,
        min_tracking_conf=0.5,
        vis_thresh=0.5,
        min_visible_landmarks=4,
        model_complexity=1,
        enable_segmentation=False,
        smooth_landmarks=True
    ):

        # -------------------------------
        # MediaPipe Pose
        # -------------------------------
        self.vis_thresh = vis_thresh
        self.min_visible_landmarks = min_visible_landmarks

        # -------------------------------
        # Resolver ruta base (DEV o EXE)
        # -------------------------------
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS   # Cuando corre dentro del .exe
        else:
            base_path = Path(__file__).resolve().parent.parent  # Cuando corre como .py


        # -------------------------------
        # Modelo IA (TensorFlow .h5)
        # -------------------------------
        if model_path is None:
            model_path = os.path.join(base_path, "pose_model.h5")

        model_path = os.path.abspath(model_path)

        if not os.path.exists(model_path):
            raise RuntimeError(f"Modelo .h5 no encontrado: {model_path}")


        try:
            self.model = tf.keras.models.load_model(model_path)
        except Exception as e:
            raise RuntimeError(f"Error cargando modelo .h5: {e}")

        # Verificar dimensión de entrada (29 features)
        input_shape = self.model.input_shape
        if input_shape[-1] != 29:
            raise RuntimeError(f"El modelo espera {input_shape[-1]} features, pero el sistema genera 29")

        # Clases (exactamente las del entrenamiento)
        self.classes = ["standing", "sitting", "lying", "fall"]

        # Umbral de confianza
        self.min_confidence = 0.50

        # Filtro anti-ruido
        self.min_body_height = 0.25
        
        #numero para indicar que no se pudo calcular un angulo
        self.INVALID_ANGLE = -1.0

        # -------------------------------
        # MediaPipe
        # -------------------------------
        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=min_detection_conf,
            min_tracking_confidence=min_tracking_conf,
            model_complexity=model_complexity,
            enable_segmentation=enable_segmentation,
            smooth_landmarks=smooth_landmarks
        )

        self.LM = mp.solutions.pose.PoseLandmark

    # ---------------------------------------------------------------------
    # MÉTODO PRINCIPAL: analiza un frame
    # ---------------------------------------------------------------------
    def analyze(self, frame):
        # =========================================================
        # 1️⃣ PREPROCESAMIENTO DE IMAGEN
        # =========================================================
        # MediaPipe usa RGB, OpenCV usa BGR → conversión necesaria
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        # Si no hay esqueleto detectado → no hay persona
        if not results.pose_landmarks:
            return {"present": False}

        lm = results.pose_landmarks.landmark

        # =========================================================
        # 2️⃣ VISIBILIDAD GLOBAL (calidad del esqueleto)
        # =========================================================
        # Si muchos puntos son invisibles → no confiable
        vis_count = sum(p.visibility >= self.vis_thresh for p in lm)
        present = vis_count >= self.min_visible_landmarks
        if not present:
            return {"present": False}

        # =========================================================
        # FUNCIONES AUXILIARES
        # =========================================================
        def L(i):
            lm_i = lm[i]
            return lm_i if lm_i.visibility >= self.vis_thresh else None
        
        def avg2(a, b):
            if a and b: return (a + b) / 2
            if a: return a
            if b: return b
            return None

        def avg_xy(a, b):
            if a and b:
                return ((a.x + b.x)/2, (a.y + b.y)/2)
            if a:
                return (a.x, a.y)
            if b:
                return (b.x, b.y)
            return None
        
        def min2(a, b):
            if a == self.INVALID_ANGLE: return b
            if b == self.INVALID_ANGLE: return a
            return min(a, b)

        def max2(a, b):
            if a == self.INVALID_ANGLE: return b
            if b == self.INVALID_ANGLE: return a
            return max(a, b)
        
        # =========================================================
        # 3️⃣ LANDMARKS ESTRUCTURALES
        # =========================================================
        
        nose = lm[self.LM.NOSE]

        ls = lm[self.LM.LEFT_SHOULDER]
        rs = lm[self.LM.RIGHT_SHOULDER]

        lhip = lm[self.LM.LEFT_HIP]
        rhip = lm[self.LM.RIGHT_HIP]

        lk = lm[self.LM.LEFT_KNEE]
        rk = lm[self.LM.RIGHT_KNEE]

        la = lm[self.LM.LEFT_ANKLE]
        ra = lm[self.LM.RIGHT_ANKLE]

        le = lm[self.LM.LEFT_ELBOW]
        re = lm[self.LM.RIGHT_ELBOW]

        lw = lm[self.LM.LEFT_WRIST]
        rw = lm[self.LM.RIGHT_WRIST]
        


        has_shoulder = (ls is not None) or (rs is not None)
        has_hip = (lhip is not None) or (rhip is not None)

        #Considera que hay una persona si hay al menos un hombro o una cadera
        if not (has_shoulder and has_hip):
            return {"present": False}
            
        # =========================================================
        # Altura y filtros
        # =========================================================
        # Centros
        
        sc = avg_xy(ls, rs)
        hc = avg_xy(lhip, rhip)

        if sc is None or hc is None:
            return {"present": False}

        sx, sy = sc
        hx, hy = hc

        if nose is None:
            # Vector torso (cadera → hombros)
            vx = sx - hx
            vy = sy - hy
            norm = (vx*vx + vy*vy)**0.5 + 1e-6
            vx /= norm
            vy /= norm

            # Cabeza ≈ 30% del torso desde hombros
            nx = sx + vx * 0.3
            ny = sy + vy * 0.3

            nose = type("LM", (), {})()
            nose.x = nx
            nose.y = ny
        
        nose_y = nose.y
        
        hip_y = avg2(lhip.y if lhip else None, rhip.y if rhip else None)
        
        
        knee_y = avg2(lk.y if lk else None, rk.y if rk else None)
        
        if knee_y is None:
            return {"present": False}

        body_height = abs(nose_y - knee_y)
        if body_height < 0.1:  # filtro mínimo
            return {"present": False}

        # =========================================================
        # Ancho y proporciones
        # =========================================================
        if ls and rs:
            shoulder_width = abs(ls.x - rs.x)
        else:
            shoulder_width = 0.3  # promedio relativo

        if lhip and rhip:
            hip_width = abs(lhip.x - rhip.x)
        else:
            hip_width = shoulder_width * 0.8
        
        aspect_ratio = shoulder_width / max(body_height, 1e-6)

        # =========================================================
        # Torso spread
        # =========================================================
        torso_spread = math.hypot(sx - hx, sy - hy)

        # =========================================================
        # Orientación
        # =========================================================
        cx = hx * w
        cy = hy * h
        nx = nose.x * w
        ny = nose.y * h
        torso_angle = math.degrees(math.atan2(ny - cy, nx - cx))
        angle_from_vertical = abs(90 - abs(torso_angle))

        # =========================================================
        # Cabeza / horizontalidad
        # =========================================================
        head_tilt = hip_y - nose_y

        # =========================================================
        # Rodillas
        # =========================================================
        left_knee = self.angle(lhip, lk, la)
        right_knee = self.angle(rhip, rk, ra)
            
        knee_min = min2(left_knee, right_knee)
        knee_max = max2(left_knee, right_knee)
        knee_diff = abs(left_knee - right_knee) if left_knee != -1 and right_knee != -1 else 0

        # =========================================================
        # Colinealidad
        # =========================================================
        left_line = self.angle(ls, lhip, lk)
        right_line = self.angle(rs, rhip, rk)
        
        body_line_min = min2(left_line, right_line)
        body_line_max = max2(left_line, right_line)
        body_line_diff = abs(left_line - right_line) if left_line != -1 and right_line != -1 else 0

        # =========================================================
        # Asimetría lateral
        # =========================================================
        shoulder_y_diff = abs(ls.y - rs.y) if ls and rs else 0
        hip_y_diff = abs(lhip.y - rhip.y) if lhip and rhip else 0
        knee_y_diff = abs(lk.y - rk.y) if lk and rk else 0

        # =========================================================
        # Brazos y codos
        # =========================================================
        left_elbow = self.angle(ls, le, lw)
        right_elbow = self.angle(rs, re, rw)
        
        elbow_min = min2(left_elbow, right_elbow)
        elbow_max = max2(left_elbow, right_elbow)
        elbow_diff = abs(left_elbow - right_elbow) if left_elbow != -1 and right_elbow != -1 else 0

        
        wrist_y_avg = avg2(lw.y if lw else None, rw.y if rw else None)
        if wrist_y_avg is None:
            wrist_below_hip = False
        else:
            wrist_below_hip = wrist_y_avg > hip_y

        # =========================================================
        # Cabeza y hombros
        # =========================================================
        shoulder_y_avg = avg2(ls.y if ls else None, rs.y if rs else None)
        shoulder_x_avg = avg2(ls.x if ls else None, rs.x if rs else None)

        if shoulder_y_avg is None:
            head_below_shoulders = False
            head_offset_x = 0
        else:
            head_below_shoulders = nose.y > shoulder_y_avg
            head_offset_x = abs(nose.x - shoulder_x_avg)
        
        
        if ls:
            head_to_left_shoulder = math.hypot(nose.x - ls.x, nose.y - ls.y)
        else:
            head_to_left_shoulder = 999

        if rs:
            head_to_right_shoulder = math.hypot(nose.x - rs.x, nose.y - rs.y)
        else:
            head_to_right_shoulder = 999
            
        head_shoulder_min = min(head_to_left_shoulder, head_to_right_shoulder)
        head_shoulder_diff = abs(head_to_left_shoulder - head_to_right_shoulder)

        # =========================================================
        # SALIDA FINAL — FEATURES PARA IA
        # =========================================================
        return {
            "present": True,
            "landmarks": results.pose_landmarks,
            "visibility_count": vis_count,

            # Forma global
            "body_height": body_height,
            "shoulder_width": shoulder_width,
            "hip_width": hip_width,
            "aspect_ratio": aspect_ratio,
            "torso_spread": torso_spread,

            # Orientación
            "torso_angle": torso_angle,
            "angle_from_vertical": angle_from_vertical,
            "head_tilt": head_tilt,

            # Piernas
            "knee_left": left_knee,
            "knee_right": right_knee,
            "knee_min": knee_min,
            "knee_max": knee_max,
            "knee_diff": knee_diff,

            # Colinealidad
            "body_line_min": body_line_min,
            "body_line_max": body_line_max,
            "body_line_diff": body_line_diff,

            # Asimetría (caídas)
            "shoulder_y_diff": shoulder_y_diff,
            "hip_y_diff": hip_y_diff,
            "knee_y_diff": knee_y_diff,

            # Brazos
            "elbow_left": left_elbow,
            "elbow_right": right_elbow,
            "elbow_min": elbow_min,
            "elbow_max": elbow_max,
            "elbow_diff": elbow_diff,
            "wrist_below_hip": wrist_below_hip,

            # Cabeza
            "head_below_shoulders": head_below_shoulders,
            "head_offset_x": head_offset_x,
            "head_shoulder_min": head_shoulder_min,
            "head_shoulder_diff": head_shoulder_diff
        }
        
    
    # ---------------------------------------------------------------------
    # CLASIFICACIÓN DE POSE
    # ---------------------------------------------------------------------
    def clasificar_pose(self, data):

        # 0️⃣ Validación básica
        if not data or not data.get("present", False):
            return "desconocido"

        # 1️⃣ Construir vector EXACTO al dataset (29 features)
        try:
            features = np.array([[ 
                data["body_height"],
                data["shoulder_width"],
                data["hip_width"],
                data["aspect_ratio"],
                data["torso_spread"],
                data["torso_angle"],
                data["angle_from_vertical"],
                data["head_tilt"],
                data["knee_left"],
                data["knee_right"],
                data["knee_min"],
                data["knee_max"],
                data["knee_diff"],
                data["body_line_min"],
                data["body_line_max"],
                data["body_line_diff"],
                data["shoulder_y_diff"],
                data["hip_y_diff"],
                data["knee_y_diff"],
                data["elbow_left"],
                data["elbow_right"],
                data["elbow_min"],
                data["elbow_max"],
                data["elbow_diff"],
                int(data["wrist_below_hip"]),
                int(data["head_below_shoulders"]),
                data["head_offset_x"],
                data["head_shoulder_min"],
                data["head_shoulder_diff"]
            ]], dtype=np.float32)
        except KeyError:
            return "desconocido"

        # 2️⃣ Inferencia TensorFlow
        probs = self.model.predict(features, verbose=0)[0]

        # 3️⃣ Seleccionar clase
        class_id = int(np.argmax(probs))
        confidence = float(probs[class_id])
        label = self.classes[class_id]

        # 4️⃣ Umbral
        if confidence < self.min_confidence:
            return "desconocido"

        return label


    def angle(self, a,b,c):
        if a is None or b is None or c is None:
            return self.INVALID_ANGLE
        ba = np.array([a.x-b.x,a.y-b.y])
        bc = np.array([c.x-b.x,c.y-b.y])
        cos = np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc)+1e-6)
        return np.degrees(np.arccos(np.clip(cos,-1,1)))
