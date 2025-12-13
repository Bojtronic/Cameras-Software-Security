import cv2

def test_rtsp_connection(rtsp_url: str) -> bool:
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return False

    ret, _ = cap.read()
    cap.release()
    return ret
