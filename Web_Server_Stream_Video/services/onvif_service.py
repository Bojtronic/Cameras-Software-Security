from onvif import ONVIFCamera
import logging
import os
import sys


# -------------------------------------------------
# Resolver ruta WSDL (dev + exe)
# -------------------------------------------------
if getattr(sys, "frozen", False):
    # Ejecutable PyInstaller
    BASE_DIR = sys._MEIPASS
else:
    # Desarrollo normal
    BASE_DIR = os.path.dirname(__file__)

WSDL_DIR = os.path.join(BASE_DIR, "services", "wsdl")



def get_rtsp_urls(ip: str, user: str, password: str, port: int = 80):
    """
    Obtiene URLs RTSP desde una cámara ONVIF por IP directa.
    No usa discovery, no crea threads, no usa UDP.
    """

    try:
        cam = ONVIFCamera(
            host=ip,
            port=port,
            user=user,
            passwd=password,
            wsdl_dir=WSDL_DIR
        )

        media = cam.create_media_service()
        profiles = media.GetProfiles()

        streams = []

        for profile in profiles:
            try:
                uri = media.GetStreamUri({
                    "StreamSetup": {
                        "Stream": "RTP-Unicast",
                        "Transport": {"Protocol": "RTSP"}
                    },
                    "ProfileToken": profile.token
                })

                streams.append({
                    "profile": profile.Name,
                    "rtsp": uri.Uri
                })

            except Exception as e:
                logging.warning(
                    f"Error RTSP perfil {profile.Name}: {e}"
                )

        return streams

    except Exception as e:
        logging.error(f"Error ONVIF ({ip}:{port}): {e}")
        raise RuntimeError(f"No se pudo conectar vía ONVIF a {ip}:{port}")
