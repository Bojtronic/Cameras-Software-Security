import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

CAMERA_PORTS = [80, 443, 554, 8000, 37777]
TIMEOUT = 0.4
MAX_WORKERS = 50

def get_local_subnet():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    parts = local_ip.split(".")
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

def is_port_open(ip: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            return s.connect_ex((ip, port)) == 0
    except Exception:
        return False


def scan_ip(ip: str):
    open_ports = []

    for port in CAMERA_PORTS:
        if is_port_open(ip, port):
            open_ports.append(port)

    if open_ports:
        return {
            "ip": ip,
            "ports": open_ports
        }

    return None

import socket


def scan_network(subnet: str | None = None):
    if not subnet:
        subnet = get_local_subnet()
        
    net = ipaddress.ip_network(subnet, strict=False)
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(scan_ip, str(ip)): str(ip)
            for ip in net.hosts()
        }

        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    return results
