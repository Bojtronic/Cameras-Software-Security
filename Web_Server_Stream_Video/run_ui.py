import webbrowser
import threading
import time
import uvicorn
import sys
import os

def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

if getattr(sys, "frozen", False):
    sys.path.insert(0, BASE_PATH)
    sys.path.insert(0, os.path.join(BASE_PATH, "app"))
    
def abrir_navegador():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")
    
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

