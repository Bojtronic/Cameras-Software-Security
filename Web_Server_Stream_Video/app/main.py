from fastapi import FastAPI
import uvicorn

from app.events import lifespan
from app.routers import video_router, persona_router, pose_router
from core import config

app = FastAPI(lifespan=lifespan)

# incluir routers
app.include_router(video_router.router)
app.include_router(persona_router.router)
app.include_router(pose_router.router)


@app.get('/')
async def root():
    return {"msg": "Servidor OK — visitar /video /persona /pose"}


if __name__ == '__main__':
    print(f"Servidor en http://{config.ADVERTISE_IP}:{config.PORT}/video")
    uvicorn.run('app.main:app', host=config.HOST, port=config.PORT, reload=False)
