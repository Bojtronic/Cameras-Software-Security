# app/models/network_scan.py
from pydantic import BaseModel

class NetworkScanRequest(BaseModel):
    subnet: str  # ej: "192.168.18.0/24"
