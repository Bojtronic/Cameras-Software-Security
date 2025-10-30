# main.py
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import webbrowser
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

@app.get("/ui", response_class=HTMLResponse)
def interfaz():
    html = """
    <html>
        <head>
            <title>Milestone Dashboard</title>
            <style>
                body { font-family: Arial; margin: 40px; background: #f4f4f4; }
                h1 { color: #333; }
                button { padding: 8px 16px; margin: 4px; }
                pre { background: #fff; padding: 16px; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>Milestone API Dashboard</h1>
            <button onclick="getData('/token')">Obtener Token</button>
            <button onclick="getData('/sites')">Ver Sitios</button>
            <button onclick="getData('/events')">Ver Eventos</button>
            <button onclick="getData('/alarms')">Ver Alarmas</button>
            <pre id="output">Presiona un botón para cargar datos...</pre>

            <script>
                async function getData(endpoint) {
                    const response = await fetch(endpoint);
                    const data = await response.json();
                    document.getElementById('output').textContent = JSON.stringify(data, null, 2);
                }
            </script>
        </body>
    </html>
    """
    return html

# -------------------------
# 🔹 Ejecución del servidor
# -------------------------

async def ejecutar_servidor():
    """
    Ejecuta el servidor FastAPI usando Uvicorn.
    """
    url = "http://192.168.18.26:8008/ui"
    webbrowser.open(url)
    config = uvicorn.Config(
        app,
        host="192.168.18.26",
        port=8008,
        log_level="info"
    )
    servidor = uvicorn.Server(config)
    await servidor.serve()


if __name__ == "__main__":
    print("🚀 Servidor iniciado. Abre tu navegador en http://localhost:8008/ui o http://<tu_IP>:8008/docs")
    try:
        asyncio.run(ejecutar_servidor())
    except KeyboardInterrupt:
        print("🛑 Servidor detenido por el usuario.")
