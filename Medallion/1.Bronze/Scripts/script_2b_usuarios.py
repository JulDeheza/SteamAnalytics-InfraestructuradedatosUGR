# ============================================================
# CAPA BRONZE — SCRIPT 2B: EXTRACCIÓN DE PERFILES DE USUARIO
# Ingiere perfiles públicos basados en los autores de reseñas
# ============================================================
import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.colab import userdata

BASE_DIR = Path("/content/Infraestructura-de-ciencia-de-datos/Medallion/1.Bronze/Data")
RESENAS_FILE = BASE_DIR / "resenas.json"
STEAM_IDS_FILE = BASE_DIR / "steam_ids.json"
USUARIOS_FILE = BASE_DIR / "usuarios.json"
CHECKPOINT_FILE = BASE_DIR / "Checkpoints" / "usuarios_checkpoint.json"

STEAM_API_KEY = userdata.get("STEAM_API_KEY")
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

if CHECKPOINT_FILE.exists():
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)
else:
    checkpoint = {
        "metadata": {
            "source": "ISteamUser/GetPlayerSummaries",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        "processed_steamids": [],
        "users": []
    }

with open(STEAM_IDS_FILE, "r", encoding="utf-8") as f:
    steam_ids_data = json.load(f)
steam_ids = steam_ids_data.get("steamids", [])
steam_ids = [sid for sid in steam_ids if str(sid).strip().isdigit() and len(str(sid).strip()) == 17]

processed_set = set(checkpoint.setdefault("processed_steamids", []))
pendientes = [sid for sid in steam_ids if sid not in processed_set]

BATCH_SIZE = 100
SLEEP_TIME = 0.6

for i in range(0, len(pendientes), BATCH_SIZE):
    batch = pendientes[i:i + BATCH_SIZE]
    params = {"key": STEAM_API_KEY, "steamids": ",".join(batch)}
    try:
        response = session.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        players = data.get("response", {}).get("players", [])

        for player in players:
            if not any(u["steamid"] == player["steamid"] for u in checkpoint["users"]):
                checkpoint["users"].append(player)

        checkpoint["processed_steamids"].extend(batch)

        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2)
        with open(USUARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump({"metadata": checkpoint["metadata"], "users": checkpoint["users"]}, f, indent=2)

        time.sleep(SLEEP_TIME)
    except Exception as e:
        print(f"Error: {e}")
        break