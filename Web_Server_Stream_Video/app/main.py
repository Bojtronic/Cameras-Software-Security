from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, sys

from app.events import lifespan
from app.routers import video_router, persona_router, pose_router, camera_router, alert_router
from core import config

def get_base_path():
    """ Retorna la ruta base correcta para desarrollo o EXE empaquetado """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

if getattr(sys, "frozen", False):
    # En el EXE, PyInstaller mete TODO dentro de /app
    STATIC_DIR = os.path.join(BASE_PATH, "app", "static")
    TEMPLATE_DIR = os.path.join(BASE_PATH, "app", "templates")
else:
    # En modo desarrollo, las carpetas ya están dentro de /app
    STATIC_DIR = os.path.join(BASE_PATH, "static")
    TEMPLATE_DIR = os.path.join(BASE_PATH, "templates")

app = FastAPI(lifespan=lifespan)

app.include_router(video_router.router)
app.include_router(persona_router.router)
app.include_router(pose_router.router)
app.include_router(camera_router.router)
app.include_router(alert_router.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    print(f"Servidor corriendo en http://{config.ADVERTISE_IP}:{config.PORT}")
    uvicorn.run("app.main", host=config.HOST, port=config.PORT, reload=False)