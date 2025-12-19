#RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/"
#RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/cam/realmonitor?channel=1&subtype=0"
RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/cam/realmonitor?channel=1&subtype=1"


CAP_BUFFERSIZE = 1

DETECTION_CONF = 0.6
TRACKING_CONF = 0.6
VIS_THRESH = 0.6
MIN_LANDMARKS = 8
HOMBROS_MIN_PX = 30
HOMBROS_MAX_PX = 600

FRAMES_ON = 5
FRAMES_OFF = 5

ENABLE_ONVIF = False

POSE_COLORS = {
    "de_pie": (0, 255, 0),
    "sentado": (0, 200, 255),
    "acostado": (255, 200, 0),
    "caido": (0, 0, 255),
    "desconocido": (200, 200, 200)
}

# Host/port defaults para desarrollo
HOST = "0.0.0.0"
PORT = 8010

# IP para mostrar en consola (opcional)
ADVERTISE_IP = "127.0.0.1"
