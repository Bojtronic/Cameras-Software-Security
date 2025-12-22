#RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/"
#RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/cam/realmonitor?channel=1&subtype=0"
#RTSP_URL = "rtsp://admin:TIss9831@192.168.18.14:554/cam/realmonitor?channel=1&subtype=1"


# ==========================
# MediaPipe Pose – Config
# ==========================

# Confianza mínima para detección inicial de la persona.
# Se usa cuando MediaPipe intenta detectar una pose desde cero.
# Valores más altos:
#   - Menos falsos positivos
#   - Más riesgo de perder detecciones lejanas o parciales
# Valores recomendados:
#   - Cámaras cercanas / buena iluminación: 0.6 – 0.7
#   - Cámaras lejanas / ángulo alto: 0.4 – 0.5
DETECTION_CONF = 0.5


# Confianza mínima para el tracking entre frames consecutivos.
# Una vez detectada la pose, este valor controla si se sigue
# reutilizando la detección anterior.
# Valores más bajos:
#   - Tracking más estable
#   - Puede mantener errores por más tiempo
# Valores más altos:
#   - Más reinicios del modelo
#   - Más consumo de CPU
TRACKING_CONF = 0.4


# Complejidad del modelo de MediaPipe Pose:
# 0 = Muy rápido, menos preciso (ideal para hardware limitado)
# 1 = Balance entre velocidad y precisión (RECOMENDADO)
# 2 = Más preciso, mayor uso de CPU/GPU
#
# Recomendación:
#   - CCTV / múltiples cámaras: 0 o 1
#   - Análisis crítico / una sola cámara: 2
MODEL_COMPLEXITY = 1


# Modo imagen estática:
# True  → cada frame se procesa como imagen independiente
# False → se usa tracking temporal (OBLIGATORIO para video)
#
# ⚠️ Nunca usar True en streams de video
STATIC_IMAGE_MODE = False


# Suavizado temporal de landmarks.
# Reduce vibraciones y ruido frame a frame.
# Aumenta ligeramente la latencia pero mejora estabilidad.
#
# Recomendado:
#   - True en entornos reales
#   - False solo si se necesita respuesta ultra rápida
SMOOTH_LANDMARKS = False


# Activa segmentación corporal (máscara de la persona).
# MUY costoso en CPU/GPU.
#
# Solo usar si:
#   - Necesitas separar persona del fondo
#   - O hacer análisis visual avanzado
ENABLE_SEGMENTATION = False


# Suavizado de la máscara de segmentación.
# Solo tiene efecto si ENABLE_SEGMENTATION = True
SMOOTH_SEGMENTATION = False


# Umbral mínimo de visibilidad para que un landmark sea considerado válido.
# Cada landmark tiene visibility ∈ [0,1]
#
# Valores típicos:
#   0.3 → muy permisivo (entornos difíciles)
#   0.4 – 0.5 → balanceado (RECOMENDADO)
#   0.6+ → muy estricto
VIS_THRESH = 0.4


# Número mínimo de landmarks visibles para considerar
# que hay una persona real en el frame.
#
# Valores bajos:
#   - Detecta personas parciales
#   - Más falsos positivos
# Valores altos:
#   - Más robusto
#   - Puede perder personas sentadas o parcialmente ocultas
MIN_LANDMARKS = 4


# Ancho mínimo de hombros en píxeles.
# Filtra detecciones muy pequeñas (ruido o personas muy lejanas).
#
# Ajustar según resolución:
#   - 720p: 20–30 px
#   - 1080p: 30–50 px
HOMBROS_MIN_PX = 30


# Ancho máximo de hombros en píxeles.
# Evita falsas detecciones cuando la persona está
# extremadamente cerca de la cámara.
HOMBROS_MAX_PX = 600


# Dibuja landmarks y conexiones sobre el frame.
# Usar solo para debug o calibración.
# Desactivar en producción para ahorrar CPU.
DIBUJAR = True


# Altura corporal mínima normalizada (0–1).
# Se calcula como distancia nariz–rodillas.
#
# Evita clasificar:
#   - Fragmentos
#   - Personas demasiado lejos
MIN_BODY_HEIGHT = 0.18


# Relación ancho / alto a partir de la cual
# se considera que la persona está acostada.
#
# Valores típicos:
#   0.8 → sensible
#   0.9 → balanceado (RECOMENDADO)
#   1.1 → muy estricto
ASPECT_RATIO_LYING = 1.2


# Ángulo máximo (en grados) respecto a la vertical
# para considerar que la persona está de pie o sentada.
#
# 0° = totalmente vertical
# 90° = totalmente horizontal
MAX_ANGLE_STANDING = 45


# Ángulo mínimo desde la vertical para considerar
# que la persona está acostada.
#
# Más bajo → más sensible
# Más alto → más estricto
MIN_ANGLE_LYING = 999


# Diferencia mínima entre cadera y cabeza (normalizada)
# para considerar postura vertical válida.
#
# Evita confundir personas inclinadas con acostadas.
HEAD_TILT_MIN_STANDING = 0.08


# Centro de masa máximo (eje Y normalizado)
# para considerar persona de pie.
#
# Valores bajos → persona erguida
# Valores altos → persona más baja en la imagen
COM_Y_STANDING_MAX = 0.65


# Límite superior del centro de masa para persona sentada.
# Por encima de este valor se considera pose no válida
# o acostada.
COM_Y_SITTING_MAX = 0.85

    

# Tamaño del buffer de la cámara.
# 1 = mínima latencia (RECOMENDADO)
# >1 = más estabilidad, más retraso
CAP_BUFFERSIZE = 1



AI_MAX_WIDTH = 640     # tamaño apropiado para el procesamiento de IA, buen balance
AI_MAX_HEIGHT = 640    # opcional, se usa width como referencia



CAMERA_TIMEOUT = 2.0          # segundos sin frame = caída
CAMERA_RECONNECT_COOLDOWN = 3.0
MAX_RECONNECT_ATTEMPTS = 5



# Frames consecutivos necesarios para confirmar presencia.
# Evita falsos positivos intermitentes.
FRAMES_ON = 5


# Frames consecutivos sin detección para confirmar ausencia.
FRAMES_OFF = 5


# Habilita control ONVIF (PTZ, etc.)
# Solo si el hardware lo soporta.
ENABLE_ONVIF = False


POSE_COLORS = {
    "de_pie": (0, 255, 0),        # Verde
    "sentado": (0, 200, 255),    # Amarillo azulado
    "acostado": (255, 200, 0),   # Naranja
    "caido": (0, 0, 255),        # Rojo
    "desconocido": (200, 200, 200)  # Gris
}

# Host/port defaults para desarrollo
HOST = "0.0.0.0"
PORT = 8010

# IP para mostrar en consola (opcional)
ADVERTISE_IP = "127.0.0.1"
