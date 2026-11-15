# ============================================================
# CAPA BRONZE — SCRIPT 1: CATÁLOGO DE JUEGOS
# Descarga el listado inicial de videojuegos de Steam
# ============================================================
import os
import json
import time
from datetime import datetime
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.colab import userdata

BASE_DIR = Path("/content/Infraestructura-de-ciencia-de-datos")
DATA_DIR = BASE_DIR / "Medallion" / "1.Bronze" / "Data"
OUTPUT_FILE = DATA_DIR / "juegos.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STEAM_HOST = "https://api.steampowered.com"
ENDPOINT = f"{STEAM_HOST}/IStoreService/GetAppList/v1/"
STEAM_API_KEY = userdata.get("STEAM_API_KEY")

MAX_APPS_PRODUCCION = 5000
PAGE_SIZE = 50000
SLEEP_ENTRE_REQUESTS = 1.0
TIMEOUT = 60

session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

def guardar_checkpoint(apps, last_appid):
    checkpoint = {
        "metadata": {
            "source": "Steam Web API",
            "updated_at": datetime.now().isoformat(),
            "total_apps": len(apps),
            "last_appid": last_appid
        },
        "apps": apps
    }
    temp_file = OUTPUT_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, OUTPUT_FILE)

apps = []
last_appid = 0

try:
    while len(apps) < MAX_APPS_PRODUCCION:
        restantes = MAX_APPS_PRODUCCION - len(apps)
        cantidad = min(PAGE_SIZE, restantes)
        payload = {
            "include_games": True,
            "include_dlc": False,
            "include_software": False,
            "include_videos": False,
            "include_hardware": False,
            "max_results": cantidad
        }
        if last_appid > 0:
            payload["last_appid"] = last_appid

        params = {"key": STEAM_API_KEY, "input_json": json.dumps(payload)}
        response = session.get(ENDPOINT, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        result = data.get("response", {})
        nuevos = result.get("apps", [])
        if not nuevos:
            break

        ids_existentes = {int(app["appid"]) for app in apps}
        for app in nuevos:
            if int(app["appid"]) not in ids_existentes:
                apps.append(app)

        nuevo_last_appid = max(int(app["appid"]) for app in nuevos)
        if nuevo_last_appid <= last_appid:
            break
        last_appid = nuevo_last_appid
        apps.sort(key=lambda x: int(x["appid"]))
        guardar_checkpoint(apps, last_appid)
        time.sleep(SLEEP_ENTRE_REQUESTS)
except Exception as e:
    print(f"Error: {e}")

guardar_checkpoint(apps, last_appid)