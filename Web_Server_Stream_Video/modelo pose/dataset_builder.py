import csv
import cv2
import time
from detectors.person_detector import PersonDetector
from services.camera_service import Camara

OUTPUT_FILE = "pose_dataset.csv"

LABELS = {
    "1": 0,  # standing
    "2": 1,  # sitting
    "3": 2,  # lying
    "4": 3   # fall
}

FEATURE_NAMES = [
    "body_height",
    "shoulder_width",
    "hip_width",
    "aspect_ratio",
    "torso_spread",
    "angle_from_vertical",
    "head_tilt",
    "knee_min",
    "knee_diff",
    "body_line_min",
    "body_line_diff",
    "shoulder_y_diff",
    "hip_y_diff",
    "knee_y_diff",
    "elbow_min",
    "elbow_diff",
    "wrist_below_hip",
    "head_below_shoulders",
    "head_offset_x",
    "head_shoulder_min",
    "head_shoulder_diff"
]

def safe(v):
    if v is None:
        return 0.0
    try:
        if v != v:
            return 0.0
    except:
        return 0.0
    return float(v)

def extract_features(data):
    return [
        safe(data.get("body_height")),
        safe(data.get("shoulder_width")),
        safe(data.get("hip_width")),
        safe(data.get("aspect_ratio")),
        safe(data.get("torso_spread")),
        safe(data.get("angle_from_vertical")),
        safe(data.get("head_tilt")),
        safe(data.get("knee_min")),
        safe(data.get("knee_diff")),
        safe(data.get("body_line_min")),
        safe(data.get("body_line_diff")),
        safe(data.get("shoulder_y_diff")),
        safe(data.get("hip_y_diff")),
        safe(data.get("knee_y_diff")),
        safe(data.get("elbow_min")),
        safe(data.get("elbow_diff")),
        int(data.get("wrist_below_hip", 0)),
        int(data.get("head_below_shoulders", 0)),
        safe(data.get("head_offset_x")),
        safe(data.get("head_shoulder_min")),
        safe(data.get("head_shoulder_diff")),
    ]

def main():
    RTSP_URL = "rtsp_url_aqui"   # usa la misma URL que tu sistema

    cam = Camara(RTSP_URL, buffer_size=2)
    detector = PersonDetector()

    print("\n🎥 DATASET BUILDER (pipeline real)")
    print("SPACE = congelar")
    print("1–4   = clase")
    print("s     = guardar")
    print("d     = descartar")
    print("q     = salir\n")

    try:
        file_exists = open(OUTPUT_FILE).read().strip() != ""
    except:
        file_exists = False

    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(FEATURE_NAMES + ["label"])

        frozen = False
        frozen_frame = None
        frozen_data = None
        current_label = None

        while True:
            if not frozen:
                frame = cam.obtener_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                frame_for_ai = frame.copy()
                data = detector.analyze(frame_for_ai)

                display = frame.copy()

                if data.get("landmarks"):
                    detector.draw_landmarks(display, data["landmarks"])

                cv2.imshow("Dataset Builder", display)

                key = cv2.waitKey(1) & 0xFF

                if key == ord(" "):
                    if data.get("present"):
                        frozen = True
                        frozen_frame = display.copy()
                        frozen_data = data
                        print("🧊 Frame congelado — elige clase (1–4)")
                    else:
                        print("No hay persona válida")

                elif key == ord("q"):
                    break

            else:
                cv2.imshow("Dataset Builder", frozen_frame)

                key = cv2.waitKey(1) & 0xFF

                if chr(key) in LABELS:
                    current_label = LABELS[chr(key)]
                    print(f"Clase = {current_label}. Presiona 's' para guardar o 'd' para descartar")

                elif key == ord("s") and current_label is not None:
                    features = extract_features(frozen_data)
                    writer.writerow(features + [current_label])
                    print("✔ Guardado")
                    frozen = False
                    current_label = None

                elif key == ord("d"):
                    print("✖ Descartado")
                    frozen = False
                    current_label = None

                elif key == ord("q"):
                    break

    cam.liberar()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
