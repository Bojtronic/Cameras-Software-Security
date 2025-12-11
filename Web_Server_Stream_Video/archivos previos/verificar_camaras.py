import cv2

def listar_camaras(max_camaras=10):
    """
    Detecta y lista todas las cámaras disponibles.
    
    Args:
        max_camaras (int): Número máximo de índices de cámara a revisar.
    
    Returns:
        list: Índices de las cámaras disponibles.
    """
    camaras_disponibles = []
    print("Buscando cámaras conectadas...")
    for i in range(max_camaras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Cámara {i} disponible - Resolución: {width}x{height}")
                camaras_disponibles.append(i)
            cap.release()
        else:
            cap.release()
    if not camaras_disponibles:
        print("No se encontraron cámaras disponibles.")
    return camaras_disponibles

def mostrar_camara(indice):
    """
    Muestra el video de la cámara especificada en una ventana.
    
    Args:
        indice (int): Índice de la cámara.
    """
    cap = cv2.VideoCapture(indice)
    if not cap.isOpened():
        print(f"No se pudo abrir la cámara {indice}")
        return
    
    print(f"Presiona 'q' para cerrar la cámara {indice}")
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"No se pudo leer la cámara {indice}")
            break
        cv2.imshow(f"Cámara {indice}", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyWindow(f"Cámara {indice}")

if __name__ == "__main__":
    camaras = listar_camaras(max_camaras=10)
    for cam in camaras:
        mostrar_camara(cam)
