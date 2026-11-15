
import json
import time
import os
import requests

from pathlib import Path
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.colab import userdata


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path("/content/Infraestructura-de-ciencia-de-datos")
BRONZE_DIR = BASE_DIR / "Medallion" / "1.Bronze"

SCRIPTS_DIR = BRONZE_DIR / "Scripts"
DATA_DIR = BRONZE_DIR / "Data"
CHECKPOINTS_DIR = DATA_DIR / "Checkpoints"

for folder in [SCRIPTS_DIR, DATA_DIR, CHECKPOINTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

JUEGOS_FILE = DATA_DIR / "juegos.json"
NOVEDADES_FILE = DATA_DIR / "novedades.json"
CHECKPOINT_FILE = CHECKPOINTS_DIR / "novedades_checkpoint.json"


# ============================================================
# 2. API STEAM
# ============================================================

ENDPOINT = (
    "https://api.steampowered.com/"
    "ISteamNews/GetNewsForApp/v0002/"
)

try:
    API_KEY = userdata.get("STEAM_API_KEY")
except Exception:
    API_KEY = None


# ============================================================
# 3. CONFIGURACIÓN
# ============================================================

TEST_MODE = False

APP_IDS_TEST = [
    730,  # Counter-Strike 2
    570,  # Dota 2
    440   # Team Fortress 2
]

NOTICIAS_POR_APP = 100
SLEEP_ENTRE_REQUESTS = 0.5
TIMEOUT = 60

# True: elimina el checkpoint y comienza desde cero.
# False: continúa desde el último progreso guardado.
REINICIAR_EXTRACCION = False


# ============================================================
# 4. RANGO TEMPORAL
# ============================================================

TS_INICIO = int(
    datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
)

# Límite exclusivo: 01/01/2026 00:00:00 UTC
TS_FIN_EXCLUSIVO = int(
    datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
)


# ============================================================
# 5. SESIÓN HTTP
# ============================================================

session = requests.Session()

retries = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True
)

adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)


# ============================================================
# 6. FUNCIONES AUXILIARES
# ============================================================

def guardar_json_seguro(ruta, contenido):

    temporal = ruta.with_suffix(ruta.suffix + ".tmp")

    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(
            contenido,
            archivo,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporal, ruta)


def cargar_appids():

    if not JUEGOS_FILE.exists():
        raise FileNotFoundError(
            f"No existe el catálogo: {JUEGOS_FILE}"
        )

    with open(JUEGOS_FILE, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    if isinstance(datos, dict):
        juegos = datos.get("apps", [])
    elif isinstance(datos, list):
        juegos = datos
    else:
        raise ValueError("Formato de juegos.json no reconocido.")

    appids = []
    vistos = set()

    for juego in juegos:

        if not isinstance(juego, dict):
            continue

        valor = juego.get("appid", juego.get("steam_appid"))

        try:
            appid = int(valor)
        except (TypeError, ValueError):
            continue

        if appid > 0 and appid not in vistos:
            appids.append(appid)
            vistos.add(appid)

    if not appids:
        raise ValueError("No se encontraron AppIDs válidos.")

    return appids


def cargar_checkpoint(appids):

    if REINICIAR_EXTRACCION:

        for archivo in [CHECKPOINT_FILE, NOVEDADES_FILE]:
            if archivo.exists():
                archivo.unlink()

    if CHECKPOINT_FILE.exists():

        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

        if datos.get("appids") != appids:
            raise ValueError(
                "El catálogo de AppIDs no coincide con el checkpoint. "
                "Verificá el modo de ejecución o reiniciá la extracción."
            )

        print("[Checkpoint] Progreso anterior recuperado.")

    else:

        datos = {
            "metadata": {
                "source": "ISteamNews/GetNewsForApp/v0002",
                "period_start": "2020-01-01T00:00:00+00:00",
                "period_end_exclusive": "2026-01-01T00:00:00+00:00",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "appids": appids,
            "current_app_index": 0,
            "current_enddate": TS_FIN_EXCLUSIVO,
            "completed_appids": [],
            "news": []
        }

    datos.setdefault("news", [])
    datos.setdefault("completed_appids", [])
    datos.setdefault("current_app_index", 0)
    datos.setdefault("current_enddate", TS_FIN_EXCLUSIVO)

    return datos


def guardar_progreso():

    checkpoint["metadata"]["updated_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    guardar_json_seguro(CHECKPOINT_FILE, checkpoint)
    guardar_json_seguro(NOVEDADES_FILE, checkpoint["news"])


def consultar_noticias(appid, enddate):

    parametros = {
        "appid": appid,
        "count": NOTICIAS_POR_APP,
        "maxlength": 0,
        "enddate": enddate,
        "format": "json"
    }

    if API_KEY:
        parametros["key"] = API_KEY

    respuesta = session.get(
        ENDPOINT,
        params=parametros,
        timeout=TIMEOUT
    )

    respuesta.raise_for_status()

    resultado = respuesta.json()

    return resultado.get("appnews", {}).get("newsitems", [])


# ============================================================
# 7. CARGAR APPIDS
# ============================================================

appids_catalogo = cargar_appids()

if TEST_MODE:
    APP_IDS = APP_IDS_TEST.copy()
else:
    APP_IDS = appids_catalogo.copy()

print("=" * 60)
print("SCRIPT 3 - NOVEDADES DE STEAM")
print("=" * 60)

print(f"Modo: {'PRUEBA' if TEST_MODE else 'PRODUCCIÓN'}")
print(f"Apps en catálogo: {len(appids_catalogo):,}")
print(f"Apps a consultar: {len(APP_IDS):,}")


# ============================================================
# 8. RECUPERAR CHECKPOINT
# ============================================================

checkpoint = cargar_checkpoint(APP_IDS)

ids_existentes = {
    str(noticia["gid"])
    for noticia in checkpoint["news"]
    if noticia.get("gid") is not None
}

inicio_ejecucion = time.time()

errores = 0
descartadas = 0
nuevas_noticias = 0


# ============================================================
# 9. EXTRACCIÓN DE NOTICIAS
# ============================================================

while checkpoint["current_app_index"] < len(APP_IDS):

    indice = checkpoint["current_app_index"]
    appid = APP_IDS[indice]

    enddate = checkpoint["current_enddate"]

    print(
        f"\n[Novedades] App {indice + 1}/{len(APP_IDS)} "
        f"- AppID: {appid}"
    )

    app_terminada = False
    error_app = False

    while not app_terminada:

        try:

            noticias = consultar_noticias(appid, enddate)

            if not noticias:
                print("No se encontraron más noticias.")
                app_terminada = True
                break

            fechas = []
            nuevas_pagina = 0

            for noticia in noticias:

                try:
                    fecha_unix = int(noticia.get("date", 0))
                except (TypeError, ValueError):
                    descartadas += 1
                    continue

                fechas.append(fecha_unix)

                if not (TS_INICIO <= fecha_unix < TS_FIN_EXCLUSIVO):
                    descartadas += 1
                    continue

                gid = noticia.get("gid")

                if gid is not None and str(gid) in ids_existentes:
                    continue

                noticia["_bronze_meta"] = {
                    "ingested_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "source": "steam_news_api",
                    "appid": appid,
                    "fecha_legible": datetime.fromtimestamp(
                        fecha_unix,
                        tz=timezone.utc
                    ).isoformat()
                }

                checkpoint["news"].append(noticia)

                if gid is not None:
                    ids_existentes.add(str(gid))

                nuevas_pagina += 1
                nuevas_noticias += 1

            print(f"Noticias recibidas: {len(noticias):,}")
            print(f"Nuevas noticias en rango: {nuevas_pagina:,}")

            guardar_progreso()

            if not fechas:
                app_terminada = True
                break

            fecha_mas_antigua = min(fechas)

            if fecha_mas_antigua <= TS_INICIO:
                app_terminada = True
                break

            if len(noticias) < NOTICIAS_POR_APP:
                app_terminada = True
                break

            nuevo_enddate = fecha_mas_antigua - 1

            if nuevo_enddate >= enddate:
                print("No hubo avance en la paginación.")
                app_terminada = True
                break

            enddate = nuevo_enddate
            checkpoint["current_enddate"] = enddate

            guardar_progreso()

            time.sleep(SLEEP_ENTRE_REQUESTS)

        except requests.exceptions.RequestException as error:

            errores += 1
            error_app = True

            print(f"[ERROR HTTP] AppID {appid}: {error}")
            break

        except (ValueError, KeyError, TypeError) as error:

            errores += 1
            error_app = True

            print(f"[ERROR DE DATOS] AppID {appid}: {error}")
            break

    if error_app:
        guardar_progreso()
        break

    if appid not in checkpoint["completed_appids"]:
        checkpoint["completed_appids"].append(appid)

    checkpoint["current_app_index"] += 1
    checkpoint["current_enddate"] = TS_FIN_EXCLUSIVO

    guardar_progreso()

    print(f"[Novedades] AppID {appid} completada.")

    if checkpoint["current_app_index"] < len(APP_IDS):
        time.sleep(SLEEP_ENTRE_REQUESTS)


# ============================================================
# 10. RESUMEN FINAL
# ============================================================

guardar_progreso()

tiempo_total = time.time() - inicio_ejecucion

print("\n" + "=" * 60)
print("RESUMEN BRONZE - SCRIPT 3")
print("=" * 60)

print(f"Modo: {'PRUEBA' if TEST_MODE else 'PRODUCCIÓN'}")
print(f"Apps completadas: {len(checkpoint['completed_appids']):,}")
print(f"Total de noticias almacenadas: {len(checkpoint['news']):,}")
print(f"Nuevas noticias en esta ejecución: {nuevas_noticias:,}")
print(f"Noticias descartadas: {descartadas:,}")
print(f"Errores: {errores:,}")
print(f"Tiempo: {tiempo_total:.1f} segundos")

print(f"\nDatos: {NOVEDADES_FILE}")
print(f"Checkpoint: {CHECKPOINT_FILE}")

if checkpoint["current_app_index"] >= len(APP_IDS):
    print("Estado: EXTRACCIÓN COMPLETADA")
else:
    print("Estado: PENDIENTE DE REANUDACIÓN")

print("=" * 60)
