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

    cameraStatus: document.getElementById("camera-status"),
    currentCamera: document.getElementById("currentCamera"),

    personaReal: document.getElementById("personaReal"),
    poseName: document.getElementById("poseName"),
    visibilityCount: document.getElementById("visibilityCount"),
    headTilt: document.getElementById("headTilt"),

    rtspList: document.getElementById("rtspList"),
    networkCameraList: document.getElementById("networkCameraList"),
};


// ==================================================
// HELPERS PARA INPUTS
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
    dom.videoFeed.src = "/static/no_video.png";
    videoActivo = false;
}

// ==================================================
// UTILIDADES
// ==================================================
async function postJSON(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    return res.json();
}

function buildOption(value, text, dataset = null) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.text = text;
    if (dataset) Object.assign(opt.dataset, dataset);
    return opt;
}

function injectCredentials(rtsp, user, password) {
    if (!rtsp.includes("@") && user && password) {
        return rtsp.replace(
            /^rtsp:\/\//i,
            `rtsp://${encodeURIComponent(user)}:${encodeURIComponent(password)}@`
        );
    }
    return rtsp;
}

function getCleanRTSP() {
    return dom.rtsp.value.trim();
}

// ==================================================
// ESCANEAR RED
// ==================================================
async function scanNetwork() {
    setStatus("Escaneando red local...", "loading");

    try {
        const data = await postJSON("/camera/network-scan", {});

        dom.networkCameraList.innerHTML = `<option value="">-- Seleccione una cámara --</option>`;

        if (data.success && data.devices?.length) {
            discoveredDevices = data.devices;

            const frag = document.createDocumentFragment();

            data.devices.forEach(d => {
                frag.appendChild(
                    buildOption(d.ip, `📷 ${d.ip} (puertos: ${d.ports.join(", ")})`, {
                        ports: JSON.stringify(d.ports)
                    })
                );
            });

            dom.networkCameraList.appendChild(frag);
            setStatus(`Cámaras detectadas: ${data.devices.length}`, "ok");
        } else {
            setStatus("No se detectaron cámaras en la red", "error");
        }
    } catch (e) {
        console.error(e);
        setStatus("Error escaneando red", "error");
    }
}


// ==================================================
// ONVIF
// ==================================================
async function probeOnvif() {
    setStatus("Buscando streams ONVIF...", "loading");

    try {
        const data = await postJSON("/camera/onvif-probe", {
            ip: ipEl().value,
            port: parseInt(portEl().value || "80"),
            user: userEl().value,
            password: passEl().value
        });

        dom.rtspList.innerHTML = `<option value="">-- Seleccione un stream --</option>`;

        if (data.success && data.streams?.length) {
            const frag = document.createDocumentFragment();

            data.streams.forEach(s => {
                frag.appendChild(
                    buildOption(s.rtsp, `${s.profile || "Perfil"} - ${s.rtsp}`, { rtsp: s.rtsp })

                );
            });

            dom.rtspList.appendChild(frag);
            setStatus("Streams encontrados", "ok");
        } else {
            setStatus(data.error || "No se encontraron streams", "error");
        }
    } catch (e) {
        console.error(e);
        setStatus("Error ONVIF", "error");
    }
}

async function probeOnvifFromNetwork() {
    setStatus("Consultando ONVIF...", "loading");

    const ip = document.getElementById("net_ip")?.value;
    const port = parseInt(document.getElementById("net_port")?.value || "80");
    const user = document.getElementById("net_user")?.value;
    const password = document.getElementById("net_password")?.value;

    if (!ip || !user || !password) {
        setStatus("Complete IP, usuario y contraseña", "error");
        return;
    }

    try {
        const data = await postJSON("/camera/onvif-probe", { ip, port, user, password });

        const list = document.getElementById("networkRtspList");
        if (!list) {
            setStatus("UI no contiene lista de streams", "error");
            return;
        }

        list.innerHTML = `<option value="">-- Seleccione un stream --</option>`;

        if (data.success && data.streams?.length) {
            discoveredStreams = data.streams;

            const frag = document.createDocumentFragment();

            data.streams.forEach(s => {
                frag.appendChild(
                    buildOption(s.rtsp, `${s.profile || "Perfil"} - ${s.rtsp}`, { rtsp: s.rtsp })

                );
            });

            list.appendChild(frag);
            setStatus("Streams ONVIF encontrados", "ok");
        } else {
            setStatus("No se encontraron streams ONVIF", "error");
        }
    } catch (e) {
        console.error(e);
        setStatus("Error consultando ONVIF", "error");
    }
}

// ==================================================
// SELECCIÓN DE STREAM
// ==================================================
function selectFromList() {
    const list = dom.rtspList;
    const selected = list.selectedOptions[0];
    if (!selected) return;

    let rtsp = selected.dataset.rtsp || selected.value;

    rtsp = injectCredentials(
        rtsp,
        userEl().value.trim(),
        passEl().value.trim()
    );

    rtspEl().value = rtsp;

    setStatus("RTSP seleccionado", "ok");
}



function selectNetworkStream() {
    const list = document.getElementById("networkRtspList");
    if (!list?.value) return;

    const selected = list.selectedOptions[0];
    const baseRtsp = selected?.dataset.rtsp || list.value;

    const user = document.getElementById("net_user")?.value.trim();
    const password = document.getElementById("net_password")?.value.trim();

    const rtsp = injectCredentials(baseRtsp, user, password);

    rtspEl().value = rtsp;
    setStatus("RTSP listo para probar o activar", "ok");
}


// ==================================================
// CÁMARA
// ==================================================
async function testCamera() {
    const rtsp = getCleanRTSP();

    if (!rtsp) {
        setStatus("Ingrese un RTSP", "error");
        return;
    }

    setStatus("Probando cámara...", "loading");

    try {
        const data = await postJSON("/camera/test", { rtsp });

        if (data.success) {
            setStatus("Cámara responde correctamente", "ok");
        } else {
            setStatus("RTSP inválido o sin acceso", "error");
        }
    } catch {
        setStatus("Error de conexión", "error");
    }
}

async function selectCamera() {
    const rtsp = getCleanRTSP();

    if (!rtsp) {
        setStatus("Ingrese una URL RTSP antes de activar", "error");
        return;
    }

    setStatus("Activando cámara...", "loading");

    try {
        const data = await postJSON("/camera/select", { rtsp });

        if (data.success) {
            setStatus("Cámara activada correctamente", "ok");
            cargarCamaraActual();
            refrescarVideo();
        } else {
            setStatus(data.error || "No se pudo activar la cámara", "error");
        }
    } catch (e) {
        console.error(e);
        setStatus("Error de comunicación", "error");
    }
}

function selectNetworkCamera() {
    const selected = dom.networkCameraList.selectedOptions[0];
    if (!selected) return;

    const ports = JSON.parse(selected.dataset.ports || "[]");

    dom.ip.value = dom.networkCameraList.value;
    dom.port.value = ports.includes(80) ? 80 : ports.includes(554) ? 554 : ports[0] || 80;
    dom.user.value = "";
    dom.password.value = "";

    setStatus("Cámara seleccionada, ingrese credenciales", "idle");
}


// ==================================================
// VIDEO
// ==================================================
function iniciarVideo() {
    dom.videoFeed.style.display = "block";
    videoActivo = true;
    refrescarVideo();
}

function refrescarVideo() {
    if (videoActivo) {
        dom.videoFeed.src = "/video?t=" + Date.now();
    }
}


// ==================================================
// ESTADO
// ==================================================
function setStatus(msg, type = "idle") {
    dom.cameraStatus.textContent = msg;
    dom.cameraStatus.className = `status ${type}`;
}

async function actualizarEstado() {
    try {
        const res = await fetch("/persona");
        if (!res.ok) return;

        const data = await res.json();

        dom.personaReal.textContent = data.persona_detectada ? "Sí" : "No";
        dom.poseName.textContent = data.pose || "--";
        dom.visibilityCount.textContent = data.meta?.visibility_count ?? "--";
        dom.headTilt.textContent = data.meta?.head_tilt ?? "--";
    } catch { }
}

function cargarCamaraActual() {
    fetch("/camera/current")
        .then(r => r.json())
        .then(data => {
            dom.currentCamera.textContent = data.rtsp || "No definida";
            iniciarVideo();
        });
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
setInterval(actualizarEstado, 2000);
setInterval(refrescarVideo, 1000);