import webbrowser
import threading
import time
import uvicorn
import sys
import os
import socket


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def esperar_servidor(host="127.0.0.1", port=8000, timeout=30):
    """Espera hasta que el puerto esté disponible"""
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def abrir_navegador():
    if esperar_servidor():
        webbrowser.open("http://127.0.0.1:8000/splash")


def iniciar_servidor():
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=1,
        log_config=None
    )


if __name__ == "__main__":
    threading.Thread(target=abrir_navegador, daemon=True).start()
    iniciar_servidor()
