import mediapipe as mp
import numpy as np
import cv2
import math
import onnxruntime as ort
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
        # Modelo IA (ONNX)
        # -------------------------------
        if model_path is None:
            base_path = Path(__file__).resolve().parent.parent
            model_path = base_path / "modelo pose" / "pose_model.onnx"

        model_path = str(model_path)

        if not os.path.exists(model_path):
            raise RuntimeError(f"Modelo ONNX no encontrado: {model_path}")


        try:
            self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        except Exception as e:
            raise RuntimeError(f"Error cargando modelo ONNX: {e}")
        
        
        inputs = self.session.get_inputs()
        if inputs[0].shape[-1] != 21:
            raise RuntimeError("El modelo ONNX no coincide con las 21 features del dataset")

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name


        # Clases (exactamente las del entrenamiento)
        self.classes = ["standing", "sitting", "lying", "fall"]

        # Umbral de confianza
        self.min_confidence = 0.50

        # Filtro anti-ruido
        self.min_body_height = 0.25

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
        # 3️⃣ LANDMARKS ESTRUCTURALES
        # =========================================================
        try:
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
        except:
            return {"present": False}

        # =========================================================
        # 4️⃣ ALTURA PROYECTADA (tamaño humano)
        # =========================================================
        # En cámara cenital:
        # de pie → cabeza lejos de rodillas
        # acostado → cabeza casi al mismo nivel que piernas
        nose_y = nose.y
        hip_y  = (lhip.y + rhip.y) / 2
        knee_y = (lk.y + rk.y) / 2

        body_height = abs(nose_y - knee_y)

        # Filtro anti-ruido
        if body_height < self.min_body_height:
            return {"present": False}

        # =========================================================
        # 5️⃣ ANCHO CORPORAL
        # =========================================================
        shoulder_width = abs(ls.x - rs.x)
        hip_width = abs(lhip.x - rhip.x)

        # =========================================================
        # 6️⃣ ASPECT RATIO (forma global)
        # =========================================================
        # ancho / alto
        # acostado → grande
        # de pie → pequeño
        aspect_ratio = shoulder_width / max(body_height, 1e-6)

        # =========================================================
        # 7️⃣ TORSO SPREAD (proyección real sobre el suelo)
        # =========================================================
        # Distancia hombros ↔ caderas
        # acostado → grande
        # sentado → medio
        # de pie → pequeño
        sx = (ls.x + rs.x) / 2
        sy = (ls.y + rs.y) / 2
        hx = (lhip.x + rhip.x) / 2
        hy = (lhip.y + rhip.y) / 2

        torso_spread = math.hypot(sx - hx, sy - hy)

        # =========================================================
        # 8️⃣ ORIENTACIÓN DEL CUERPO
        # =========================================================
        # Vector caderas → cabeza
        cx = hx * w
        cy = hy * h
        nx = nose.x * w
        ny = nose.y * h

        torso_angle = math.degrees(math.atan2(ny - cy, nx - cx))

        # Desviación respecto a vertical
        # 0° → vertical
        # 90° → horizontal
        angle_from_vertical = abs(90 - abs(torso_angle))

        # =========================================================
        # 9️⃣ HORIZONTALIDAD DEL CUERPO
        # =========================================================
        # cabeza muy cerca de caderas → acostado o desplome
        head_tilt = hip_y - nose_y

        # =========================================================
        # 🔟 RODILLAS (sin promediar)
        # =========================================================
        # 180° → pierna recta
        # 90° → pierna doblada (sentado)
        left_knee = self.angle(lhip, lk, la)
        right_knee = self.angle(rhip, rk, ra)

        knee_min = min(left_knee, right_knee)
        knee_max = max(left_knee, right_knee)
        knee_diff = abs(left_knee - right_knee)

        # =========================================================
        # 1️⃣1️⃣ COLINEALIDAD CORPORAL
        # =========================================================
        # hombro → cadera → rodilla
        # recto → ~180°
        # doblado → menor
        left_line = self.angle(ls, lhip, lk)
        right_line = self.angle(rs, rhip, rk)

        body_line_min = min(left_line, right_line)
        body_line_max = max(left_line, right_line)
        body_line_diff = abs(left_line - right_line)

        # =========================================================
        # 1️⃣2️⃣ ASIMETRÍA LATERAL (caídas reales)
        # =========================================================
        shoulder_y_diff = abs(ls.y - rs.y)
        hip_y_diff = abs(lhip.y - rhip.y)
        knee_y_diff = abs(lk.y - rk.y)

        # =========================================================
        # 1️⃣3️⃣ BRAZOS Y CODOS (sostén o colapso)
        # =========================================================
        left_elbow = self.angle(ls, le, lw)
        right_elbow = self.angle(rs, re, rw)

        elbow_min = min(left_elbow, right_elbow)
        elbow_max = max(left_elbow, right_elbow)
        elbow_diff = abs(left_elbow - right_elbow)

        # Muñecas colgando → brazos sin sostén
        wrist_y_avg = (lw.y + rw.y) / 2
        wrist_below_hip = wrist_y_avg > hip_y

        # =========================================================
        # 1️⃣4️⃣ CABEZA vs HOMBROS (desmayo / desplome)
        # =========================================================
        shoulder_y_avg = (ls.y + rs.y) / 2
        shoulder_x_avg = (ls.x + rs.x) / 2

        # Cabeza por debajo de los hombros → colapso
        head_below_shoulders = nose.y > shoulder_y_avg

        # Desplazamiento lateral de la cabeza
        head_offset_x = abs(nose.x - shoulder_x_avg)

        # Distancia cabeza ↔ hombros
        head_to_left_shoulder = math.hypot(nose.x - ls.x, nose.y - ls.y)
        head_to_right_shoulder = math.hypot(nose.x - rs.x, nose.y - rs.y)

        head_shoulder_min = min(head_to_left_shoulder, head_to_right_shoulder)
        head_shoulder_diff = abs(head_to_left_shoulder - head_to_right_shoulder)

        # =========================================================
        # 1️⃣5️⃣ SALIDA FINAL — FEATURES PARA IA
        # =========================================================
        return {
            "present": True,

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

        # 1️⃣ Construir vector de entrada EXACTO al entrenamiento
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

        # 2️⃣ Inferencia ONNX
        probs = self.session.run(
            [self.output_name],
            {self.input_name: features}
        )[0][0]

        # 3️⃣ Seleccionar clase
        class_id = int(np.argmax(probs))
        confidence = float(probs[class_id])
        label = self.classes[class_id]

        # 4️⃣ Umbral
        if confidence < self.min_confidence:
            return "desconocido"

        return label


    def angle(self, a, b, c):
        # ángulo ABC en grados
        ba = np.array([a.x - b.x, a.y - b.y])
        bc = np.array([c.x - b.x, c.y - b.y])
        cosang = np.dot(ba, bc) / (np.linalg.norm(ba)*np.linalg.norm(bc) + 1e-6)
        return np.degrees(np.arccos(np.clip(cosang, -1, 1)))
