import cv2
from core.config import POSE_COLORS
import mediapipe as mp


def draw_pose_on_frame(frame, landmarks):
    try:
        mp.solutions.drawing_utils.draw_landmarks(
            frame,
            landmarks,
            mp.solutions.pose.POSE_CONNECTIONS,
            mp.solutions.drawing_utils.DrawingSpec(thickness=2, circle_radius=2),
            mp.solutions.drawing_utils.DrawingSpec(thickness=2)
        )
    except Exception:
        pass


def get_pose_color(pose_name: str):
    return POSE_COLORS.get(pose_name, POSE_COLORS["desconocido"])
