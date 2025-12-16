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

async function probeOnvifFromNetwork() {
    setStatus("Consultando ONVIF...", "loading");

    const ip = document.getElementById("net_ip").value;
    const port = parseInt(document.getElementById("net_port").value || "80");
    const user = document.getElementById("net_user").value;
    const password = document.getElementById("net_password").value;

    if (!ip || !user || !password) {
        setStatus("Complete IP, usuario y contraseña", "error");
        return;
    }

    const res = await fetch("/camera/onvif-probe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip, port, user, password })
    });

    const data = await res.json();
    const list = document.getElementById("networkRtspList");
    list.innerHTML = `<option value="">-- Seleccione un stream --</option>`;

    if (data.success && data.streams.length > 0) {
        discoveredStreams = data.streams;

        data.streams.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.rtsp;
            opt.text = `${s.profile || "Perfil"} - ${s.rtsp}`;
            list.appendChild(opt);
        });

        setStatus("Streams ONVIF encontrados", "ok");
    } else {
        setStatus("No se encontraron streams ONVIF", "error");
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

function selectNetworkStream() {
    const list = document.getElementById("networkRtspList");
    if (!list.value) return;

    const user = document.getElementById("net_user").value.trim();
    const password = document.getElementById("net_password").value.trim();

    let rtsp = list.value;

    if (!rtsp.includes("@") && user && password) {
        rtsp = rtsp.replace(
            /^rtsp:\/\//i,
            `rtsp://${encodeURIComponent(user)}:${encodeURIComponent(password)}@`
        );
    }

    document.getElementById("rtsp").value = rtsp;
    setStatus("RTSP listo para probar o activar", "ok");
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

function selectNetworkCamera() {
    const list = document.getElementById("networkCameraList");
    if (!list.value) return;

    const ipInput = document.getElementById("net_ip");
    const portInput = document.getElementById("net_port");

    const selected = list.selectedOptions[0];
    const ports = JSON.parse(selected.dataset.ports || "[]");

    ipInput.value = list.value;
    portInput.value = ports.includes(80) ? 80 :
                      ports.includes(554) ? 554 :
                      ports[0] || 80;

    // Limpiar credenciales
    document.getElementById("net_user").value = "";
    document.getElementById("net_password").value = "";

    setStatus("Cámara seleccionada, ingrese credenciales", "idle");
}


async function scanNetwork() {
    setStatus("Escaneando red local...", "loading");

    const res = await fetch("/camera/network-scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
        // 👈 NO se envía nada
    });

    const data = await res.json();

    const networkList = document.getElementById("networkCameraList");
    networkList.innerHTML = `<option value="">-- Seleccione una cámara --</option>`;

    if (data.success && data.devices.length > 0) {
        discoveredDevices = data.devices;

        data.devices.forEach(d => {
            const opt = document.createElement("option");
            opt.value = d.ip;
            opt.text = `📷 ${d.ip} (puertos: ${d.ports.join(", ")})`;
            opt.dataset.ports = JSON.stringify(d.ports);
            networkList.appendChild(opt);
        });

        setStatus(`Cámaras detectadas: ${data.devices.length}`, "ok");
    } else {
        setStatus("No se detectaron cámaras en la red", "error");
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
