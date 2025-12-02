# src/person_detector.py

import cv2
import mediapipe as mp

class PersonDetector:
    """
    Detecta si hay una persona presente en un frame usando Mediapipe Pose.
    """

    def __init__(self, min_detection_conf=0.5, min_tracking_conf=0.5, dibujar=False):
        """
        :param min_detection_conf: confianza mínima de detección inicial
        :param min_tracking_conf: confianza mínima para el seguimiento
        :param dibujar: si True, dibuja los landmarks sobre el frame
        """
        self.dibujar = dibujar

        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            min_detection_confidence=min_detection_conf,
            min_tracking_confidence=min_tracking_conf
        )

        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

    def hay_persona(self, frame):
        """
        Determina si hay una persona en el frame.

        :param frame: imagen en BGR
        :return: (bool, landmarks_opcionales)
        """

        if frame is None:
            return False, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        # Si no hay landmarks, no hay persona
        if not results.pose_landmarks:
            return False, None

        # Opcionalmente dibujar
        if self.dibujar:
            self.mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )

        return True, results.pose_landmarks

    def liberar(self):
        """Por compatibilidad con tu sistema (no hace falta liberar mediapipe)."""
        pass
