import csv
import cv2
import time
import mediapipe as mp
import numpy as np
import math
import tkinter as tk
from PIL import Image, ImageTk
from services.camera_service import Camara

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
    "angle_from_vertical","head_tilt","knee_min","knee_diff",
    "body_line_min","body_line_diff","shoulder_y_diff","hip_y_diff","knee_y_diff",
    "elbow_min","elbow_diff","wrist_below_hip","head_below_shoulders",
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
        safe(d["body_height"]), safe(d["shoulder_width"]), safe(d["hip_width"]),
        safe(d["aspect_ratio"]), safe(d["torso_spread"]), safe(d["angle_from_vertical"]),
        safe(d["head_tilt"]), safe(d["knee_min"]), safe(d["knee_diff"]),
        safe(d["body_line_min"]), safe(d["body_line_diff"]), safe(d["shoulder_y_diff"]),
        safe(d["hip_y_diff"]), safe(d["knee_y_diff"]), safe(d["elbow_min"]),
        safe(d["elbow_diff"]), int(d["wrist_below_hip"]), int(d["head_below_shoulders"]),
        safe(d["head_offset_x"]), safe(d["head_shoulder_min"]), safe(d["head_shoulder_diff"])
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
pose = mp_pose.Pose()

# =============================
# ANALYZE
# =============================
def analyze(frame):
    h,w = frame.shape[:2]
    rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    r = pose.process(rgb)
    if not r.pose_landmarks:
        return None

    lm = r.pose_landmarks.landmark
    LM = mp_pose.PoseLandmark

    nose=lm[LM.NOSE]; ls=lm[LM.LEFT_SHOULDER]; rs=lm[LM.RIGHT_SHOULDER]
    lhip=lm[LM.LEFT_HIP]; rhip=lm[LM.RIGHT_HIP]
    lk=lm[LM.LEFT_KNEE]; rk=lm[LM.RIGHT_KNEE]
    la=lm[LM.LEFT_ANKLE]; ra=lm[LM.RIGHT_ANKLE]
    le=lm[LM.LEFT_ELBOW]; re=lm[LM.RIGHT_ELBOW]
    lw=lm[LM.LEFT_WRIST]; rw=lm[LM.RIGHT_WRIST]

    nose_y=nose.y; hip_y=(lhip.y+rhip.y)/2; knee_y=(lk.y+rk.y)/2
    body_height=abs(nose_y-knee_y)
    if body_height<0.25: return None

    shoulder_width=abs(ls.x-rs.x)
    hip_width=abs(lhip.x-rhip.x)
    aspect_ratio=shoulder_width/body_height

    sx=(ls.x+rs.x)/2; sy=(ls.y+rs.y)/2
    hx=(lhip.x+rhip.x)/2; hy=(lhip.y+rhip.y)/2
    torso_spread=math.hypot(sx-hx,sy-hy)

    cx=hx*w; cy=hy*h; nx=nose.x*w; ny=nose.y*h
    torso_angle=math.degrees(math.atan2(ny-cy,nx-cx))
    angle_from_vertical=abs(90-abs(torso_angle))
    head_tilt=hip_y-nose_y

    lknee=angle(lhip,lk,la); rknee=angle(rhip,rk,ra)
    knee_min=min(lknee,rknee); knee_diff=abs(lknee-rknee)

    ll=angle(ls,lhip,lk); rl=angle(rs,rhip,rk)
    body_line_min=min(ll,rl); body_line_diff=abs(ll-rl)

    shoulder_y_diff=abs(ls.y-rs.y)
    hip_y_diff=abs(lhip.y-rhip.y)
    knee_y_diff=abs(lk.y-rk.y)

    lel=angle(ls,le,lw); rel=angle(rs,re,rw)
    elbow_min=min(lel,rel); elbow_diff=abs(lel-rel)

    wrist_below_hip=((lw.y+rw.y)/2)>hip_y
    shoulder_y_avg=(ls.y+rs.y)/2; shoulder_x_avg=(ls.x+rs.x)/2
    head_below_shoulders=nose.y>shoulder_y_avg
    head_offset_x=abs(nose.x-shoulder_x_avg)

    hls=math.hypot(nose.x-ls.x,nose.y-ls.y)
    hrs=math.hypot(nose.x-rs.x,nose.y-rs.y)

    return {
        "body_height":body_height,"shoulder_width":shoulder_width,"hip_width":hip_width,
        "aspect_ratio":aspect_ratio,"torso_spread":torso_spread,
        "angle_from_vertical":angle_from_vertical,"head_tilt":head_tilt,
        "knee_min":knee_min,"knee_diff":knee_diff,
        "body_line_min":body_line_min,"body_line_diff":body_line_diff,
        "shoulder_y_diff":shoulder_y_diff,"hip_y_diff":hip_y_diff,"knee_y_diff":knee_y_diff,
        "elbow_min":elbow_min,"elbow_diff":elbow_diff,
        "wrist_below_hip":wrist_below_hip,"head_below_shoulders":head_below_shoulders,
        "head_offset_x":head_offset_x,
        "head_shoulder_min":min(hls,hrs),"head_shoulder_diff":abs(hls-hrs),
        "landmarks":r.pose_landmarks
    }

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
                if self.data:
                    mp_draw.draw_landmarks(self.frame,self.data["landmarks"],mp_pose.POSE_CONNECTIONS)

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
