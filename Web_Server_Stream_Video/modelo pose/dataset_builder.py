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

INVALID_ANGLE = -1.0

def angle(a,b,c):
        if a is None or b is None or c is None:
            return INVALID_ANGLE
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
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
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

    
    def L(i):
        lm_i = lm[i]
        return lm_i if lm_i.visibility > 0.4 else None
    
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
        if a == INVALID_ANGLE: return b
        if b == INVALID_ANGLE: return a
        return min(a, b)

    def max2(a, b):
        if a == INVALID_ANGLE: return b
        if b == INVALID_ANGLE: return a
        return max(a, b)
    
    nose = L(LM.NOSE)
    ls = L(LM.LEFT_SHOULDER)
    rs = L(LM.RIGHT_SHOULDER)
    lhip = L(LM.LEFT_HIP)
    rhip = L(LM.RIGHT_HIP)
    lk = L(LM.LEFT_KNEE)
    rk = L(LM.RIGHT_KNEE)
    la = L(LM.LEFT_ANKLE)
    ra = L(LM.RIGHT_ANKLE)
    le = L(LM.LEFT_ELBOW)
    re = L(LM.RIGHT_ELBOW)
    lw = L(LM.LEFT_WRIST)
    rw = L(LM.RIGHT_WRIST)

    has_shoulder = (ls is not None) or (rs is not None)
    has_hip = (lhip is not None) or (rhip is not None)

    #Considera que hay una persona si hay al menos un hombro o una cadera
    if not (has_shoulder and has_hip):
        return {"present": False}
    

    # =========================================================
    # 3️⃣ Altura y filtros
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
    # 4️⃣ Ancho y proporciones
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
    # 5️⃣ Torso spread
    # =========================================================
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
        
    knee_min = min2(left_knee, right_knee)
    knee_max = max2(left_knee, right_knee)
    knee_diff = abs(left_knee - right_knee) if left_knee != -1 and right_knee != -1 else 0

    # =========================================================
    # 9️⃣ Colinealidad
    # =========================================================
    left_line = angle(ls, lhip, lk)
    right_line = angle(rs, rhip, rk)
    
    body_line_min = min2(left_line, right_line)
    body_line_max = max2(left_line, right_line)
    body_line_diff = abs(left_line - right_line) if left_line != -1 and right_line != -1 else 0

    # =========================================================
    # 🔟 Asimetría lateral
    # =========================================================
    shoulder_y_diff = abs(ls.y - rs.y) if ls and rs else 0
    hip_y_diff = abs(lhip.y - rhip.y) if lhip and rhip else 0
    knee_y_diff = abs(lk.y - rk.y) if lk and rk else 0

    # =========================================================
    # 1️⃣1️⃣ Brazos y codos
    # =========================================================
    left_elbow = angle(ls, le, lw)
    right_elbow = angle(rs, re, rw)
    
    elbow_min = min2(left_elbow, right_elbow)
    elbow_max = max2(left_elbow, right_elbow)
    elbow_diff = abs(left_elbow - right_elbow) if left_elbow != -1 and right_elbow != -1 else 0

    
    wrist_y_avg = avg2(lw.y if lw else None, rw.y if rw else None)
    if wrist_y_avg is None:
        wrist_below_hip = False
    else:
        wrist_below_hip = wrist_y_avg > hip_y

    # =========================================================
    # 1️⃣2️⃣ Cabeza y hombros
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

        POSE_BUTTON_COLORS = {
            "standing": "#0000FF",   # 🔵 Azul
            "sitting":  "#00FF00",   # 🟢 Verde
            "lying":    "#FFA500",   # 🟠 Naranja
            "fall":     "#FF0000",   # 🔴 Rojo
        }
        
        ACTIVE_GRAY = "#444444"

        tk.Button(
            self.controls,
            text="❄ Freeze",
            font=btn_font,
            width=10,
            bg="#777777",
            fg="white",
            activebackground=ACTIVE_GRAY,
            activeforeground="white",
            relief="raised",
            bd=3,
            command=self.freeze
        ).pack(side="left", padx=10)

        for k in LABELS:
            color = POSE_BUTTON_COLORS.get(k.lower(), "#C8C8C8")

            tk.Button(
                self.controls,
                text=k.capitalize(),
                font=btn_font,
                width=10,
                bg=color,
                fg="white",
                activebackground=ACTIVE_GRAY, 
                activeforeground="white",
                relief="raised",
                bd=3,
                command=lambda k=k: self.set_label(k)
            ).pack(side="left", padx=5)

        tk.Button(
            self.controls,
            text="💾 Save",
            font=btn_font,
            width=10,
            bg="#777777",
            fg="white",
            activebackground=ACTIVE_GRAY,
            activeforeground="white",
            relief="raised",
            bd=3,
            command=self.save
        ).pack(side="left", padx=10)

        tk.Button(
            self.controls,
            text="✖ Discard",
            font=btn_font,
            width=10,
            bg="#777777",
            fg="white",
            activebackground=ACTIVE_GRAY,
            activeforeground="white",
            relief="raised",
            bd=3,
            command=self.discard
        ).pack(side="left", padx=10)

        tk.Button(
            self.controls,
            text="⛔ Exit",
            font=btn_font,
            width=10,
            bg="#444444",
            fg="white",
            activebackground="#FF4444",
            activeforeground="white",
            relief="raised",
            bd=3,
            command=self.exit
        ).pack(side="right", padx=20)

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
