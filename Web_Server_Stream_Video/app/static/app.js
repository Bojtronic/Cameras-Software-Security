let discoveredDevices = [];
let discoveredStreams = [];

const ipEl = () => document.getElementById("ip");
const userEl = () => document.getElementById("user");
const passEl = () => document.getElementById("password");
const portEl = () => document.getElementById("port");
const rtspEl = () => document.getElementById("rtsp");



async function probeOnvif() {
    setStatus("Buscando streams ONVIF...", "loading");

    const ip = ipEl().value;
    const user = userEl().value;
    const password = passEl().value;
    const port = parseInt(portEl().value || "80");

    const res = await fetch("/camera/onvif-probe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip, port, user, password })
    });

    const data = await res.json();

    const list = document.getElementById("rtspList");
    list.innerHTML = `<option value="">-- Seleccione un stream --</option>`;

    if (data.success && data.streams.length > 0) {
        data.streams.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.rtsp;
            opt.text = `${s.profile || "Perfil"} - ${s.rtsp}`;
            list.appendChild(opt);
        });
        setStatus("Streams encontrados", "ok");
    } else {
        setStatus(data.error || "No se encontraron streams", "error");
    }
}


function selectFromList() {
    const list = document.getElementById("rtspList");
    const rtspInput = document.getElementById("rtsp");

    const user = userEl().value.trim();
    const password = passEl().value.trim();

    if (!list.value) return;

    let rtsp = list.value;

    // Insertar credenciales si NO existen
    if (!rtsp.includes("@") && user && password) {
        rtsp = rtsp.replace(
            /^rtsp:\/\//i,
            `rtsp://${encodeURIComponent(user)}:${encodeURIComponent(password)}@`
        );
    }

    rtspInput.value = rtsp;
    setStatus("RTSP seleccionado", "ok");
}





async function testCamera() {
    const rtsp = rtspEl().value;
    setStatus("Probando cámara...", "loading");

    const res = await fetch("/camera/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rtsp })
    });

    const data = await res.json();
    setStatus(
        data.success ? "Cámara responde correctamente" : "Error al conectar",
        data.success ? "ok" : "error"
    );
}


async function selectCamera() {
    const rtsp = rtspEl().value;

    const res = await fetch("/camera/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rtsp })
    });

    const data = await res.json();

    if (data.success) {
        setStatus("Cámara activada", "ok");
        cargarCamaraActual();
        refrescarVideo();
    }
}

function refrescarVideo() {
    const img = document.getElementById("videoFeed");
    img.src = "/video?t=" + Date.now();
}

function setStatus(msg, type = "idle") {
    const el = document.getElementById("camera-status");
    el.innerText = msg;
    el.className = `status ${type}`;
}



function setStatus(msg) {
  document.getElementById("camera-status").innerText = msg;
}


function actualizarEstado() {
    fetch("/persona")
        .then(r => {
            if (!r.ok) throw new Error("Respuesta no OK");
            return r.json();
        })
        .then(data => {
            document.getElementById("personaReal").innerText =
                data.persona_detectada ? "Sí" : "No";

            document.getElementById("poseName").innerText =
                data.pose || "--";

            document.getElementById("visibilityCount").innerText =
                data.meta?.visibility_count ?? "--";

            document.getElementById("headTilt").innerText =
                data.meta?.head_tilt ?? "--";
        })
        .catch(e => log("Error obteniendo estado: " + e));
}

function cargarCamaraActual() {
    fetch("/camera/current")
        .then(r => r.json())
        .then(data => {
            document.getElementById("currentCamera").innerText =
                data.rtsp || "No definida";
        })
        .catch(e => console.error(e));
}

cargarCamaraActual();

// Actualizar cada 2 segundos
setInterval(actualizarEstado, 2000);
