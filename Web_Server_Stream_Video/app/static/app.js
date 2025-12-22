// ==================================================
// ESTADO GLOBAL
// ==================================================
let discoveredDevices = [];
let discoveredStreams = [];
let videoActivo = false;

// ==================================================
// CACHE DE ELEMENTOS DOM (mejora rendimiento)
// ==================================================
const dom = {
    ip: document.getElementById("ip"),
    user: document.getElementById("user"),
    password: document.getElementById("password"),
    port: document.getElementById("port"),
    rtsp: document.getElementById("rtsp"),

    videoFeed: document.getElementById("videoFeed"),
    videoPlaceholder: document.getElementById("video-placeholder"),

    cameraStatus: document.getElementById("camera-status"),
    currentCamera: document.getElementById("currentCamera"),

    personaReal: document.getElementById("personaReal"),
    poseName: document.getElementById("poseName"),
    visibilityCount: document.getElementById("visibilityCount"),
    headTilt: document.getElementById("headTilt"),
};

// ==================================================
// HELPERS PARA INPUTS (se mantienen nombres)
// ==================================================
const ipEl = () => dom.ip;
const userEl = () => dom.user;
const passEl = () => dom.password;
const portEl = () => dom.port;
const rtspEl = () => dom.rtsp;

// ==================================================
// UI
// ==================================================
function toggleSidebar() {
    document.getElementById("sidebar")?.classList.toggle("closed");
}

function resetVideoUI() {
    dom.videoFeed.src = "static/no_video.png";
    videoActivo = false;
}

// ==================================================
// ONVIF
// ==================================================
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

// ==================================================
// SELECCIÓN DE STREAM
// ==================================================
function selectFromList() {
    const list = document.getElementById("rtspList");
    if (!list?.value) return;

    let rtsp = list.value;
    const user = userEl().value.trim();
    const password = passEl().value.trim();

    if (!rtsp.includes("@") && user && password) {
        rtsp = rtsp.replace(
            /^rtsp:\/\//i,
            `rtsp://${encodeURIComponent(user)}:${encodeURIComponent(password)}@`
        );
    }

    rtspEl().value = rtsp;
    setStatus("RTSP seleccionado", "ok");
}

function selectNetworkStream() {
    const list = document.getElementById("networkRtspList");
    if (!list?.value) return;

    let rtsp = list.value;
    const user = document.getElementById("net_user").value.trim();
    const password = document.getElementById("net_password").value.trim();

    if (!rtsp.includes("@") && user && password) {
        rtsp = rtsp.replace(
            /^rtsp:\/\//i,
            `rtsp://${encodeURIComponent(user)}:${encodeURIComponent(password)}@`
        );
    }

    rtspEl().value = rtsp;
    setStatus("RTSP listo para probar o activar", "ok");
}

// ==================================================
// CÁMARA
// ==================================================
async function testCamera() {
    setStatus("Probando cámara...", "loading");

    const res = await fetch("/camera/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rtsp: rtspEl().value })
    });

    const data = await res.json();
    setStatus(
        data.success ? "Cámara responde correctamente" : "Error al conectar",
        data.success ? "ok" : "error"
    );
}

async function selectCamera() {
    const rtsp = rtspEl().value.trim();

    if (!rtsp) {
        setStatus("Ingrese una URL RTSP antes de activar", "error");
        return;
    }

    if (!rtsp.toLowerCase().startsWith("rtsp://")) {
        setStatus("La URL debe comenzar con rtsp://", "error");
        return;
    }

    setStatus("Activando cámara...", "loading");

    try {
        const res = await fetch("/camera/select", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rtsp })
        });

        const data = await res.json();

        if (data.success) {
            setStatus("Cámara activada correctamente", "ok");
            cargarCamaraActual();
        } else {
            setStatus(data.error || "No se pudo activar la cámara", "error");
        }
    } catch (err) {
        console.error(err);
        setStatus("Error de comunicación con el servidor", "error");
    }
}

// ==================================================
// VIDEO
// ==================================================
function iniciarVideo() {
    dom.videoFeed.style.display = "block";
    dom.videoPlaceholder.style.display = "none";

    videoActivo = true;
    refrescarVideo();
}

function refrescarVideo() {
    if (!videoActivo) return;

    dom.videoFeed.src = "/video?t=" + Date.now();
}

// ==================================================
// ESTADO
// ==================================================
function setStatus(msg, type = "idle") {
    dom.cameraStatus.innerText = msg;
    dom.cameraStatus.className = `status ${type}`;
}

async function actualizarEstado() {
    try {
        const res = await fetch("/persona");
        if (!res.ok) throw new Error("Respuesta no OK");

        const data = await res.json();

        dom.personaReal.innerText = data.persona_detectada ? "Sí" : "No";
        dom.poseName.innerText = data.pose || "--";
        dom.visibilityCount.innerText = data.meta?.visibility_count ?? "--";
        dom.headTilt.innerText = data.meta?.head_tilt ?? "--";

    } catch (e) {
        console.warn("Error obteniendo estado:", e);
    }
}

function cargarCamaraActual() {
    fetch("/camera/current")
        .then(r => r.json())
        .then(data => {
            dom.currentCamera.innerText = data.rtsp || "No definida";
            iniciarVideo(); // activar video solo cuando hay cámara
        })
        .catch(e => console.error(e));
}

// ==================================================
// ALERTAS
// ==================================================
async function enviarAlertaWhatsApp_1() {
    await fetch("/alerts/sendWhatsApp1", { method: "POST" });
}

async function enviarAlertaCorreo_1() {
    await fetch("/alerts/sendEmail1", { method: "POST" });
}

async function enviarAlertaWhatsApp_2() {
    const res = await fetch("/alerts/sendWhatsApp2");
    const data = await res.json();
    window.open(data.url, "_blank", "noopener,noreferrer");
}

async function enviarAlertaCorreo_2() {
    const res = await fetch("/alerts/sendEmail2");
    const data = await res.json();
    window.open(data.url, "_blank", "noopener,noreferrer");
}

// ==================================================
// INICIO
// ==================================================
resetVideoUI();

//cargarCamaraActual();

// Estado cada 2 segundos
setInterval(actualizarEstado, 2000);

// Video solo si está activo
setInterval(refrescarVideo, 1000);
