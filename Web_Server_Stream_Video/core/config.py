# ============================================================
#                MediaPipe Pose – CONFIGURACIÓN
#        para cámaras cenitales (desde techo)
# ============================================================


# ------------------------------------------------------------
# CONFIANZA DE DETECCIÓN INICIAL
# ------------------------------------------------------------
# Probabilidad mínima para que MediaPipe acepte que
# una figura humana ha sido detectada en un frame.
#
# Controla cuántos "fantasmas" acepta el modelo.
#
# Valores bajos (0.3–0.4):
#   - Detecta personas muy pequeñas o lejanas
#   - Aumentan sombras y falsos positivos
#
# Valores altos (0.6–0.8):
#   - Solo personas claras
#   - Puede perder personas en el suelo o parcialmente visibles
#
DETECTION_CONF = 0.4


# ------------------------------------------------------------
# CONFIANZA DE TRACKING TEMPORAL
# ------------------------------------------------------------
# Controla si MediaPipe sigue una detección previa
# o fuerza una nueva detección.
#
# Bajo → tracking estable (pero puede arrastrar errores)
# Alto → más reinicios (más CPU)
#
TRACKING_CONF = 0.4


# ------------------------------------------------------------
# COMPLEJIDAD DEL MODELO DE POSE
# ------------------------------------------------------------
# 0 → Rápido, menos precisión
# 1 → Balanceado (RECOMENDADO)
# 2 → Muy preciso, más lento
#
MODEL_COMPLEXITY = 1


# ------------------------------------------------------------
# MODO DE PROCESAMIENTO
# ------------------------------------------------------------
# False = usa tracking temporal (OBLIGATORIO en video)
# True  = cada frame es independiente (solo para fotos)
#
STATIC_IMAGE_MODE = False


# ------------------------------------------------------------
# SUAVIZADO DE LANDMARKS
# ------------------------------------------------------------
# Reduce vibraciones del esqueleto entre frames.
# Aumenta latencia ~1–2 frames.
#
SMOOTH_LANDMARKS = False


# ------------------------------------------------------------
# SEGMENTACIÓN CORPORAL
# ------------------------------------------------------------
# Genera una máscara binaria del cuerpo.
# MUY costoso → solo activar si es necesario.
#
ENABLE_SEGMENTATION = False
SMOOTH_SEGMENTATION = False


# ------------------------------------------------------------
# VISIBILIDAD DE LANDMARKS
# ------------------------------------------------------------
# Cada punto tiene confidence ∈ [0,1]
# Este umbral define cuándo se considera confiable.
#
# 0.3 → muy permisivo
# 0.4–0.5 → ideal
# 0.6+ → muy estricto
#
VIS_THRESH = 0.4


# ------------------------------------------------------------
# LANDMARKS MÍNIMOS
# ------------------------------------------------------------
# Cantidad mínima de puntos visibles para
# aceptar que hay una persona real.
#
# Bajo → detecta fragmentos
# Alto → puede perder personas sentadas o caídas
#
MIN_LANDMARKS = 4


# ------------------------------------------------------------
# FILTRO DE TAMAÑO HUMANO
# ------------------------------------------------------------
# Distancia mínima entre hombros en píxeles.
# Evita detectar manchas pequeñas.
#
HOMBROS_MIN_PX = 20

# Evita detectar "gigantes" (errores cuando la cámara
# está muy cerca o se detectan dos personas como una).
#
HOMBROS_MAX_PX = 600


# ------------------------------------------------------------
# VISUALIZACIÓN
# ------------------------------------------------------------
# Dibujar esqueleto sobre la imagen
# Usar solo para calibración
#
DIBUJAR = True


# ------------------------------------------------------------
# ALTURA CORPORAL NORMALIZADA
# ------------------------------------------------------------
# Distancia nariz → rodillas
# Representa el "tamaño real" de la persona en la imagen.
#
# Filtra:
#   - sombras
#   - mascotas
#   - objetos
#
MIN_BODY_HEIGHT = 0.10


# ------------------------------------------------------------
# RELACIÓN ANCHO / ALTO
# ------------------------------------------------------------
# Cuánto espacio horizontal ocupa el cuerpo
#
# De pie: bajo
# Acostado: alto
#
ASPECT_RATIO_LYING = 0.9


# ------------------------------------------------------------
# ANGULOS (NO USADOS EN CENITAL, SE DEJAN POR COMPATIBILIDAD)
# ------------------------------------------------------------
MAX_ANGLE_STANDING = 999
MIN_ANGLE_LYING = 999


# ------------------------------------------------------------
# DIFERENCIA CABEZA ↔ CADERA
# ------------------------------------------------------------
# Evita confundir personas dobladas con acostadas
#
HEAD_TILT_MIN_STANDING = 0.10


# ------------------------------------------------------------
# CENTRO DE MASA (EJE Y)
# ------------------------------------------------------------
# Valores bajos → persona más arriba
# Valores altos → persona más cerca del piso
#
COM_Y_STANDING_MAX = 0.70
COM_Y_SITTING_MAX = 0.90
COM_Y_LYING_MIN = 0.60


# ------------------------------------------------------------
# EXPANSIÓN DEL TORSO
# ------------------------------------------------------------
# Distancia hombros ↔ caderas
# Es la PROYECCIÓN del cuerpo en el suelo.
#
# De pie → pequeño
# Sentado → medio
# Acostado → grande
#
TORSO_EXPAND_MIN_LYING = 0.6
TORSO_SPREAD_LYING = 0.10


# ------------------------------------------------------------
# ALINEACIÓN CORPORAL
# ------------------------------------------------------------
# Cuánto se alinean hombros–caderas–pies
# Alto → cuerpo estirado
#
BODY_LINE_ANGLE = 150


# ------------------------------------------------------------
# ÁNGULOS DE RODILLA
# ------------------------------------------------------------
# Sentado → rodillas dobladas
# De pie → rodillas casi rectas
#
KNEE_ANGLE_SITTING_MAX = 140
KNEE_ANGLE_STANDING_MIN = 150


# ------------------------------------------------------------
# CÁMARA
# ------------------------------------------------------------
CAP_BUFFERSIZE = 1


# ------------------------------------------------------------
# RESOLUCIÓN DE IA
# ------------------------------------------------------------
# Tamaño al que se redimensiona el frame antes de IA
# Mejora velocidad sin perder estructura corporal
#
AI_MAX_WIDTH = 640
AI_MAX_HEIGHT = 640


# ------------------------------------------------------------
# TIMEOUTS DE CÁMARA
# ------------------------------------------------------------
CAMERA_TIMEOUT = 5.0
CAMERA_RECONNECT_COOLDOWN = 5.0
MAX_RECONNECT_ATTEMPTS = 5


# ------------------------------------------------------------
# FPS DINÁMICO
# ------------------------------------------------------------
AI_FPS_MIN = 2.0
AI_FPS_MAX = 12.0

# Tiempo objetivo por frame de IA
AI_TARGET_INFERENCE = 0.08   # 80 ms

# Suavizado EMA del FPS
AI_SMOOTHING = 0.9


# ------------------------------------------------------------
# FILTRO TEMPORAL DE PRESENCIA
# ------------------------------------------------------------
FRAMES_ON = 5
FRAMES_OFF = 5


# ------------------------------------------------------------
# CONTROL DE CÁMARA PTZ
# ------------------------------------------------------------
ENABLE_ONVIF = False


# ------------------------------------------------------------
# COLORES DE ESTADO
# ------------------------------------------------------------
POSE_COLORS = {
    "standing": (255, 0, 0),      # 🔵 Azul
    "sitting":  (0, 255, 0),      # 🟢 Verde
    "lying":    (0, 165, 255),    # 🟠 Naranja
    "fall":     (0, 0, 255),      # 🔴 Rojo
    "desconocido": (200, 200, 200)
}

# ------------------------------------------------------------
# RED
# ------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8010
ADVERTISE_IP = "127.0.0.1"
