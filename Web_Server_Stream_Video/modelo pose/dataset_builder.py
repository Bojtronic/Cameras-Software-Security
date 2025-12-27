import csv
import cv2
import time
import mediapipe as mp
import numpy as np
import math
import tkinter as tk
from PIL import Image, ImageTk
from services.camera_service import Camara
import threading

# =============================
# CONFIG
# =============================
OUTPUT_FILE = "pose_dataset.csv"

LABELS = {
    "Standing": 0,
    "Sitting": 1,
    "Lying": 2,
    "Fall": 3
}

FEATURE_NAMES = [
    "body_height","shoulder_width","hip_width","aspect_ratio","torso_spread",
    "torso_angle","angle_from_vertical","head_tilt",
    "knee_left","knee_right","knee_min","knee_max","knee_diff",
    "body_line_min","body_line_max","body_line_diff",
    "shoulder_y_diff","hip_y_diff","knee_y_diff",
    "elbow_left","elbow_right","elbow_min","elbow_max","elbow_diff",
    "wrist_below_hip","head_below_shoulders",
    "head_offset_x","head_shoulder_min","head_shoulder_diff"
]

# =============================
# UTILS
# =============================
def safe(v):
    if v is None or v != v:
        return 0.0
    return float(v)

def extract_features(d):
    return [
        safe(d["body_height"]), 
        safe(d["shoulder_width"]), 
        safe(d["hip_width"]),
        safe(d["aspect_ratio"]), 
        safe(d["torso_spread"]), 
        safe(d["torso_angle"]),
        safe(d["angle_from_vertical"]), 
        safe(d["head_tilt"]),
        safe(d["knee_left"]), 
        safe(d["knee_right"]), 
        safe(d["knee_min"]), 
        safe(d["knee_max"]), 
        safe(d["knee_diff"]),
        safe(d["body_line_min"]), 
        safe(d["body_line_max"]), 
        safe(d["body_line_diff"]),
        safe(d["shoulder_y_diff"]), 
        safe(d["hip_y_diff"]), 
        safe(d["knee_y_diff"]),
        safe(d["elbow_left"]), 
        safe(d["elbow_right"]), 
        safe(d["elbow_min"]), 
        safe(d["elbow_max"]), 
        safe(d["elbow_diff"]),
        int(d["wrist_below_hip"]), 
        int(d["head_below_shoulders"]),
        safe(d["head_offset_x"]), 
        safe(d["head_shoulder_min"]), 
        safe(d["head_shoulder_diff"])
    ]

def angle(a,b,c):
    ba = np.array([a.x-b.x,a.y-b.y])
    bc = np.array([c.x-b.x,c.y-b.y])
    cos = np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc)+1e-6)
    return np.degrees(np.arccos(np.clip(cos,-1,1)))

# =============================
# MEDIAPIPE
# =============================
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.15,
    min_tracking_confidence=0.15,
    smooth_landmarks=True,
    enable_segmentation=False
)


# =============================
# ANALYZE
# =============================
def analyze(frame):
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb)

    # =========================================================
    # 1️⃣ Validar presencia de persona
    # =========================================================
    if not results.pose_landmarks:
        return {"present": False}

    lm = results.pose_landmarks.landmark
    LM = mp_pose.PoseLandmark

    # =========================================================
    # 2️⃣ Manejo seguro de landmarks
    # =========================================================
    try:
        nose = lm[LM.NOSE]
        ls = lm[LM.LEFT_SHOULDER]
        rs = lm[LM.RIGHT_SHOULDER]
        lhip = lm[LM.LEFT_HIP]
        rhip = lm[LM.RIGHT_HIP]
        lk = lm[LM.LEFT_KNEE]
        rk = lm[LM.RIGHT_KNEE]
        la = lm[LM.LEFT_ANKLE]
        ra = lm[LM.RIGHT_ANKLE]
        le = lm[LM.LEFT_ELBOW]
        re = lm[LM.RIGHT_ELBOW]
        lw = lm[LM.LEFT_WRIST]
        rw = lm[LM.RIGHT_WRIST]
    except:
        return {"present": False}

    # =========================================================
    # 3️⃣ Altura y filtros
    # =========================================================
    nose_y = nose.y
    hip_y = (lhip.y + rhip.y) / 2
    knee_y = (lk.y + rk.y) / 2
    body_height = abs(nose_y - knee_y)
    if body_height < 0.25:  # filtro mínimo
        return {"present": False}

    # =========================================================
    # 4️⃣ Ancho y proporciones
    # =========================================================
    shoulder_width = abs(ls.x - rs.x)
    hip_width = abs(lhip.x - rhip.x)
    aspect_ratio = shoulder_width / max(body_height, 1e-6)

    # =========================================================
    # 5️⃣ Torso spread
    # =========================================================
    sx = (ls.x + rs.x) / 2
    sy = (ls.y + rs.y) / 2
    hx = (lhip.x + rhip.x) / 2
    hy = (lhip.y + rhip.y) / 2
    torso_spread = math.hypot(sx - hx, sy - hy)

    # =========================================================
    # 6️⃣ Orientación
    # =========================================================
    cx = hx * w
    cy = hy * h
    nx = nose.x * w
    ny = nose.y * h
    torso_angle = math.degrees(math.atan2(ny - cy, nx - cx))
    angle_from_vertical = abs(90 - abs(torso_angle))

    # =========================================================
    # 7️⃣ Cabeza / horizontalidad
    # =========================================================
    head_tilt = hip_y - nose_y

    # =========================================================
    # 8️⃣ Rodillas
    # =========================================================
    left_knee = angle(lhip, lk, la)
    right_knee = angle(rhip, rk, ra)
    knee_min = min(left_knee, right_knee)
    knee_max = max(left_knee, right_knee)
    knee_diff = abs(left_knee - right_knee)

    # =========================================================
    # 9️⃣ Colinealidad
    # =========================================================
    left_line = angle(ls, lhip, lk)
    right_line = angle(rs, rhip, rk)
    body_line_min = min(left_line, right_line)
    body_line_max = max(left_line, right_line)
    body_line_diff = abs(left_line - right_line)

    # =========================================================
    # 🔟 Asimetría lateral
    # =========================================================
    shoulder_y_diff = abs(ls.y - rs.y)
    hip_y_diff = abs(lhip.y - rhip.y)
    knee_y_diff = abs(lk.y - rk.y)

    # =========================================================
    # 1️⃣1️⃣ Brazos y codos
    # =========================================================
    left_elbow = angle(ls, le, lw)
    right_elbow = angle(rs, re, rw)
    elbow_min = min(left_elbow, right_elbow)
    elbow_max = max(left_elbow, right_elbow)
    elbow_diff = abs(left_elbow - right_elbow)

    wrist_y_avg = (lw.y + rw.y) / 2
    wrist_below_hip = wrist_y_avg > hip_y

    # =========================================================
    # 1️⃣2️⃣ Cabeza y hombros
    # =========================================================
    shoulder_y_avg = (ls.y + rs.y) / 2
    shoulder_x_avg = (ls.x + rs.x) / 2
    head_below_shoulders = nose.y > shoulder_y_avg
    head_offset_x = abs(nose.x - shoulder_x_avg)
    head_to_left_shoulder = math.hypot(nose.x - ls.x, nose.y - ls.y)
    head_to_right_shoulder = math.hypot(nose.x - rs.x, nose.y - rs.y)
    head_shoulder_min = min(head_to_left_shoulder, head_to_right_shoulder)
    head_shoulder_diff = abs(head_to_left_shoulder - head_to_right_shoulder)

    # =========================================================
    # 1️⃣3️⃣ Retorno de features
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

        # Asimetría
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
        "head_shoulder_diff": head_shoulder_diff,

        # Landmarks originales
        "landmarks": results.pose_landmarks
    }



class CamaraAsync:
    def __init__(self, cam: Camara):
        self.cam = cam
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while self.running:
            f = self.cam.obtener_frame()  # tu método original
            if f is not None:
                with self.lock:
                    self.frame = f

    def obtener_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def liberar(self):
        self.running = False
        self.cam.liberar()
        
# =============================
# GUI
# =============================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dataset Builder")

        # 🔳 Pantalla completa
        self.root.attributes("-fullscreen", True)

        # Resolución real de pantalla
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Altura reservada para botones
        self.control_h = 120
        self.video_h = self.screen_h - self.control_h

        # Cámara
        self.cam = Camara(
            "rtsp://telecom:TIss9831@192.168.18.44:554/Streaming/Channels/101?transportmode=unicast&profile=Profile_1",
            2
        )
        
        self.cam = CamaraAsync(self.cam)

        self.label = None
        self.frozen = False
        self.data = None
        self.frame = None

        # ===========================
        # VIDEO AREA
        # ===========================
        self.video_frame = tk.Frame(self.root, bg="black", height=self.video_h)
        self.video_frame.pack(fill="both", expand=True)

        self.video = tk.Label(self.video_frame, bg="black")
        self.video.pack(expand=True)

        # ===========================
        # CONTROL BAR
        # ===========================
        self.controls = tk.Frame(self.root, height=self.control_h, bg="#222")
        self.controls.pack(fill="x")

        btn_font = ("Segoe UI", 16, "bold")

        tk.Button(self.controls, text="❄ Freeze", font=btn_font, width=10,
                command=self.freeze).pack(side="left", padx=10)

        for k in LABELS:
            tk.Button(self.controls, text=k, font=btn_font, width=10,
                    command=lambda k=k: self.set_label(k)).pack(side="left", padx=5)

        tk.Button(self.controls, text="💾 Save", font=btn_font, width=10,
                command=self.save).pack(side="left", padx=10)

        tk.Button(self.controls, text="✖ Discard", font=btn_font, width=10,
                command=self.discard).pack(side="left", padx=10)

        tk.Button(self.controls, text="⛔ Exit", font=btn_font, width=10,
                command=self.exit).pack(side="right", padx=20)

        # ===========================
        # CSV
        # ===========================
        self.csv = open(OUTPUT_FILE, "a", newline="")
        self.writer = csv.writer(self.csv)

        # Loop
        self.loop()
        self.root.mainloop()

    def loop(self):
        if not self.frozen:
            self.frame=self.cam.obtener_frame()
            if self.frame is not None:
                self.data=analyze(self.frame)
                # Dibujar solo si hay persona presente
                if self.data.get("present", False):
                    mp_draw.draw_landmarks(self.frame, self.data["landmarks"], mp_pose.POSE_CONNECTIONS)


        if self.frame is not None:
            img = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)

            # Mantener proporción
            h, w = img.shape[:2]
            scale = min(self.screen_w / w, self.video_h / h)
            nw = int(w * scale)
            nh = int(h * scale)

            img = cv2.resize(img, (nw, nh))
            img = ImageTk.PhotoImage(Image.fromarray(img))

            self.video.imgtk = img
            self.video.config(image=img)
            
            
        self.root.after(30,self.loop)

    def freeze(self): self.frozen=True
    def discard(self): self.frozen=False
    def set_label(self,k): self.label=LABELS[k]
    def save(self):
        if self.data and self.label is not None:
            self.writer.writerow(extract_features(self.data)+[self.label])
            self.csv.flush()
            self.frozen=False

    def exit(self):
        self.csv.close()
        self.cam.liberar()
        self.root.destroy()

# =============================
App()
