# milestone_client.py
import requests
from config import MILESTONE_HOST, USERNAME, PASSWORD, CLIENT_ID, TOKEN_URL, API_BASE

class MilestoneClient:
    def __init__(self):
        self.token = None

    def authenticate(self):
        """Obtiene un token Bearer del IDP de Milestone."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "password",
            "username": USERNAME,
            "password": PASSWORD,
            "client_id": CLIENT_ID
        }

        response = requests.post(TOKEN_URL, headers=headers, data=data, verify=False)
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token

    def get_headers(self):
        if not self.token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    def get_sites(self):
        """Obtiene los sitios configurados."""
        url = f"{API_BASE}/sites"
        response = requests.get(url, headers=self.get_headers(), verify=False)
        response.raise_for_status()
        return response.json()

    def get_events(self):
        """Obtiene eventos del sistema."""
        url = f"{API_BASE}/events"
        response = requests.get(url, headers=self.get_headers(), verify=False)
        response.raise_for_status()
        return response.json()

    def get_alarms(self):
        """Obtiene alarmas registradas."""
        url = f"{API_BASE}/alarms"
        response = requests.get(url, headers=self.get_headers(), verify=False)
        response.raise_for_status()
        return response.json()
