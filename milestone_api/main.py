# main.py
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from milestone_client import MilestoneClient

app = FastAPI(title="Milestone API Gateway Proxy", version="1.0")

client = MilestoneClient()


@app.get("/")
def root():
    return {"mensaje": "API local para Milestone XProtect funcionando"}


@app.get("/token")
def get_token():
    try:
        token = client.authenticate()
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sites")
def get_sites():
    try:
        return client.get_sites()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
def get_events():
    try:
        return client.get_events()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alarms")
def get_alarms():
    try:
        return client.get_alarms()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# 🔹 Ejecución del servidor
# -------------------------

async def ejecutar_servidor():
    """
    Ejecuta el servidor FastAPI usando Uvicorn.
    """
    config = uvicorn.Config(
        app,
        host="192.168.18.26",
        port=8008,
        log_level="info"
    )
    servidor = uvicorn.Server(config)
    await servidor.serve()


if __name__ == "__main__":
    print("🚀 Servidor iniciado. Abre tu navegador en http://localhost:8008 o http://<tu_IP>:8008/docs")
    try:
        asyncio.run(ejecutar_servidor())
    except KeyboardInterrupt:
        print("🛑 Servidor detenido por el usuario.")
