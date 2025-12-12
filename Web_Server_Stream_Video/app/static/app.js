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

            log("Estado actualizado");
        })
        .catch(e => log("Error obteniendo estado: " + e));
}

function log(text) {
    const logs = document.getElementById("logs");
    logs.innerHTML += "> " + text + "<br>";
    logs.scrollTop = logs.scrollHeight;
}

// Actualizar cada 2 segundos
setInterval(actualizarEstado, 2000);
