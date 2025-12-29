import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"   # 0=todo, 1=info, 2=warning, 3=error

os.environ["GLOG_minloglevel"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import warnings
warnings.filterwarnings("ignore")

import webbrowser
import threading
import time
import uvicorn
import sys
import socket
import signal


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def esperar_servidor(host="127.0.0.1", port=8000, timeout=30):
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


def manejar_cierre(sig=None, frame=None):
    print("\n🛑 Señal de cierre recibida")
    print("🧹 Cerrando servidor y liberando recursos...")
    sys.exit(0)


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

    # Registrar señales del sistema
    signal.signal(signal.SIGINT, manejar_cierre)
    signal.signal(signal.SIGTERM, manejar_cierre)

    # Abrir navegador cuando el server esté listo
    threading.Thread(target=abrir_navegador, daemon=True).start()

    # Iniciar servidor (bloqueante)
    iniciar_servidor()
