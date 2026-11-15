
import json
import time
import requests

from pathlib import Path
from datetime import datetime, timezone

# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path("/content/Infraestructura-de-ciencia-de-datos")
BRONZE_DIR = BASE_DIR / "Medallion" / "1.Bronze"

DATA_DIR = BRONZE_DIR / "Data"
CHECKPOINTS_DIR = DATA_DIR / "Checkpoints"

JUEGOS_FILE = DATA_DIR / "juegos.json"
RESENAS_FILE = DATA_DIR / "resenas.json"
CHECKPOINT_FILE = CHECKPOINTS_DIR / "resenas_checkpoint.json"

for folder in [DATA_DIR, CHECKPOINTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

ENDPOINT = (
    "https://api.steampowered.com/"
    "IUserReviewsService/GetAppReviews/v1/"
)

MAX_JUEGOS_A_PROCESAR = 500
REVIEWS_TARGET_PER_APP = 100
REVIEWS_PER_PAGE = 100

# Primera ejecución: probar con Half-Life.
# Producción: cambiar MODO_PRUEBA a False.

MODO_PRUEBA = False
APPID_PRUEBA = 70

# Pausa entre páginas.
SLEEP_ENTRE_PAGINAS = 3

# Reintentos ante errores transitorios.
MAX_REINTENTOS = 4
TIMEOUT = 60

# ============================================================
# 3. SESIÓN HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
})

# ============================================================
# 4. EXCEPCIONES
# ============================================================

class ErrorSteam(Exception):
    pass


class RateLimitError(ErrorSteam):
    pass


# ============================================================
# 5. FUNCIONES DE GUARDADO
# ============================================================

def guardar_json_seguro(ruta, contenido):

    temporal = ruta.with_suffix(".tmp")

    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(
            contenido,
            f,
            ensure_ascii=False,
            indent=2
        )

    temporal.replace(ruta)


def guardar_checkpoint(checkpoint):
    guardar_json_seguro(CHECKPOINT_FILE, checkpoint)


def guardar_resenas(resenas):
    guardar_json_seguro(RESENAS_FILE, resenas)


# ============================================================
# 6. NORMALIZACIÓN Y DEDUPLICACIÓN
# ============================================================

def normalizar_resena(resena, appid):

    if not isinstance(resena, dict):
        return None

    author = resena.get("author", {})

    if not isinstance(author, dict):
        return None

    steamid = author.get("steamid")

    if not steamid:
        return None

    resena["appid"] = int(appid)
    resena["steamid"] = str(steamid)

    return resena


def clave_resena(resena):

    recommendationid = resena.get("recommendationid")

    if recommendationid is not None:
        return str(recommendationid)

    return "|".join([
        str(resena.get("appid", "")),
        str(resena.get("steamid", "")),
        str(resena.get("timestamp_created", "")),
        str(resena.get("review", ""))[:200]
    ])


# ============================================================
# 7. SOLICITUD A LA API OFICIAL
# ============================================================

def consultar_steam(appid, cursor):

    parametros = {
        "appid": int(appid),
        "filter": 1,
        "languages": ["all"],
        "review_type": 0,
        "purchase_type": 1,
        "num_per_page": REVIEWS_PER_PAGE,
        "cursor": cursor
    }

    params_http = {
        "input_json": json.dumps(parametros)
    }

    for intento in range(MAX_REINTENTOS + 1):

        try:

            response = session.get(
                ENDPOINT,
                params=params_http,
                timeout=TIMEOUT
            )

        except requests.exceptions.RequestException as e:

            if intento >= MAX_REINTENTOS:
                raise ErrorSteam(
                    f"Error de conexión después de "
                    f"{MAX_REINTENTOS} reintentos: {e}"
                )

            espera = min(30 * (2 ** intento), 300)

            print(
                f"[CONEXIÓN] Intento {intento + 1}. "
                f"Esperando {espera} segundos."
            )

            time.sleep(espera)
            continue

        # --------------------------------------------
        # CONTROL HTTP 429
        # --------------------------------------------

        if response.status_code == 429:

            if intento >= MAX_REINTENTOS:
                raise RateLimitError(
                    "Steam continúa rechazando las solicitudes "
                    "por límite de frecuencia."
                )

            retry_after = response.headers.get("Retry-After")

            try:
                espera = int(retry_after)
            except (TypeError, ValueError):
                espera = min(60 * (2 ** intento), 900)

            print(
                f"[RATE LIMIT] Steam respondió HTTP 429. "
                f"Esperando {espera} segundos."
            )

            time.sleep(espera)
            continue

        # --------------------------------------------
        # ERRORES TEMPORALES DEL SERVIDOR
        # --------------------------------------------

        if response.status_code in [500, 502, 503, 504]:

            if intento >= MAX_REINTENTOS:
                raise ErrorSteam(
                    f"Steam devolvió HTTP {response.status_code}"
                )

            espera = min(30 * (2 ** intento), 300)

            print(
                f"[SERVIDOR] HTTP {response.status_code}. "
                f"Esperando {espera} segundos."
            )

            time.sleep(espera)
            continue

        if response.status_code != 200:

            raise ErrorSteam(
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        # --------------------------------------------
        # VALIDAR JSON
        # --------------------------------------------

        try:
            resultado = response.json()

        except ValueError:

            raise ErrorSteam(
                "Steam respondió HTTP 200, "
                "pero el contenido no es JSON válido. "
                f"Contenido: {response.text[:500]}"
            )

        data = resultado.get("response")

        if not isinstance(data, dict):

            raise ErrorSteam(
                "La respuesta no contiene el objeto 'response'. "
                f"Claves recibidas: {list(resultado.keys())}"
            )

        return data

    raise ErrorSteam("No se pudo completar la consulta.")


# ============================================================
# 8. CARGAR CATÁLOGO DE JUEGOS
# ============================================================

if not JUEGOS_FILE.exists():
    raise FileNotFoundError(JUEGOS_FILE)

with open(JUEGOS_FILE, "r", encoding="utf-8") as f:
    data_juegos = json.load(f)

if isinstance(data_juegos, dict):
    lista_juegos = data_juegos.get("apps", [])
else:
    lista_juegos = data_juegos

appids_disponibles = []

for juego in lista_juegos:

    if not isinstance(juego, dict):
        continue

    try:
        appid = int(juego["appid"])
        appids_disponibles.append(appid)

    except (KeyError, ValueError, TypeError):
        continue

appids_disponibles = list(dict.fromkeys(appids_disponibles))

if MODO_PRUEBA:

    if APPID_PRUEBA not in appids_disponibles:
        raise ValueError(
            f"AppID {APPID_PRUEBA} no encontrado en juegos.json"
        )

    appids_a_procesar = [APPID_PRUEBA]

else:

    appids_a_procesar = (
        appids_disponibles[:MAX_JUEGOS_A_PROCESAR]
    )

# ============================================================
# 9. CARGAR CHECKPOINT Y MIGRAR DATOS ANTERIORES
# ============================================================

if CHECKPOINT_FILE.exists():

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)

    print("[INFO] Checkpoint existente recuperado.")

else:

    checkpoint = {}

checkpoint.setdefault("resenas", [])

# La versión anterior utilizaba otro endpoint y otros cursores.
# No reutilizamos sus estados de paginación ni sus juegos
# marcados como procesados.
#
# Conservamos únicamente las reseñas válidas y las deduplicamos.

if checkpoint.get("schema_version") != 2:

    print("[MIGRACIÓN] Actualizando checkpoint a API nueva.")

    checkpoint["procesados"] = []
    checkpoint["progreso"] = {}
    checkpoint["schema_version"] = 2

    resenas_migradas = []
    claves_migradas = set()

    for r in checkpoint["resenas"]:

        if not isinstance(r, dict):
            continue

        try:
            appid = int(r["appid"])
        except (KeyError, ValueError, TypeError):
            continue

        r = normalizar_resena(r, appid)

        if r is None:
            continue

        clave = clave_resena(r)

        if clave not in claves_migradas:
            claves_migradas.add(clave)
            resenas_migradas.append(r)

    checkpoint["resenas"] = resenas_migradas

else:

    checkpoint.setdefault("procesados", [])
    checkpoint.setdefault("progreso", {})

    resenas_migradas = []
    claves_migradas = set()

    for r in checkpoint["resenas"]:

        if not isinstance(r, dict):
            continue

        try:
            appid = int(r["appid"])
        except (KeyError, ValueError, TypeError):
            continue

        r = normalizar_resena(r, appid)

        if r is None:
            continue

        clave = clave_resena(r)

        if clave not in claves_migradas:
            claves_migradas.add(clave)
            resenas_migradas.append(r)

    checkpoint["resenas"] = resenas_migradas

claves_resenas = set(
    clave_resena(r) for r in checkpoint["resenas"]
)

procesados = set(
    int(x) for x in checkpoint["procesados"]
)

# Guardar la migración antes de comenzar.

guardar_checkpoint(checkpoint)
guardar_resenas(checkpoint["resenas"])

# ============================================================
# 10. PREPARAR EXTRACCIÓN
# ============================================================

ids_pendientes = [
    appid for appid in appids_a_procesar
    if appid not in procesados
]

resenas_nuevas = 0
errores = 0
detener_proceso = False

print("=" * 65)
print("SCRIPT 2C - EXTRACCIÓN DE RESEÑAS STEAM")
print("=" * 65)

print(f"Juegos seleccionados: {len(appids_a_procesar)}")
print(f"Juegos pendientes: {len(ids_pendientes)}")
print(f"Reseñas acumuladas: {len(checkpoint['resenas'])}")

# ============================================================
# 11. EXTRACCIÓN Y PAGINACIÓN
# ============================================================

try:

    for idx, appid in enumerate(ids_pendientes, 1):

        print("\n" + "-" * 65)

        print(
            f"[JUEGO {idx}/{len(ids_pendientes)}] "
            f"AppID: {appid}"
        )

        progreso = checkpoint["progreso"].get(
            str(appid),
            {}
        )

        cursor = progreso.get("cursor", "*")

        resenas_juego_actual = sum(
            1 for r in checkpoint["resenas"]
            if int(r["appid"]) == appid
        )

        print(
            f"Reseñas acumuladas: {resenas_juego_actual}"
        )

        juego_completado = False

        while resenas_juego_actual < REVIEWS_TARGET_PER_APP:

            try:

                data = consultar_steam(appid, cursor)

            except RateLimitError as e:

                errores += 1

                print(f"[RATE LIMIT CRÍTICO] {e}")
                print(
                    "[PAUSA GLOBAL] Se detiene toda la extracción "
                    "para no seguir enviar solicitudes."
                )

                detener_proceso = True
                break

            except ErrorSteam as e:

                errores += 1

                print(f"[ERROR] AppID {appid}: {e}")
                print(
                    "[PAUSA GLOBAL] Se conserva el cursor "
                    "y se detiene el proceso."
                )

                detener_proceso = True
                break

            reviews = data.get("reviews", [])
            total_matching = data.get("total_matching")

            if not isinstance(reviews, list):

                print("[ERROR] El campo reviews no es una lista.")
                errores += 1
                detener_proceso = True
                break

            if not reviews:

                print("[INFO] Steam no devolvió más reseñas.")

                juego_completado = True
                break

            nuevas_pagina = 0
            sin_steamid = 0

            for resena in reviews:

                resena = normalizar_resena(resena, appid)

                if resena is None:
                    sin_steamid += 1
                    continue

                clave = clave_resena(resena)

                if clave in claves_resenas:
                    continue

                checkpoint["resenas"].append(resena)
                claves_resenas.add(clave)

                nuevas_pagina += 1
                resenas_nuevas += 1
                resenas_juego_actual += 1

            print(
                f"[PÁGINA] Recibidas: {len(reviews)} | "
                f"Nuevas: {nuevas_pagina} | "
                f"Sin SteamID: {sin_steamid}"
            )

            if total_matching is not None:
                print(f"[STEAM] Total coincidente: {total_matching}")

            nuevo_cursor = data.get("cursor")

            # Si alcanzamos el objetivo, no necesitamos
            # consultar más páginas de este juego.

            if resenas_juego_actual >= REVIEWS_TARGET_PER_APP:

                juego_completado = True

                print(
                    f"[OBJETIVO] Alcanzadas "
                    f"{resenas_juego_actual} reseñas."
                )

                break

            # Sin cursor significa que no hay otra página.

            if not nuevo_cursor:

                juego_completado = True

                print("[INFO] No existe un cursor siguiente.")
                break

            if nuevo_cursor == cursor:

                print(
                    "[ERROR] Steam devolvió el mismo cursor. "
                    "Se detiene para evitar un bucle."
                )

                errores += 1
                detener_proceso = True
                break

            cursor = nuevo_cursor

            # Guardar el cursor de la siguiente página.

            checkpoint["progreso"][str(appid)] = {
                "cursor": cursor,
                "resenas_obtenidas": resenas_juego_actual,
                "completado": False,
                "actualizado_utc": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            guardar_checkpoint(checkpoint)
            guardar_resenas(checkpoint["resenas"])

            time.sleep(SLEEP_ENTRE_PAGINAS)

        # --------------------------------------------
        # FINALIZACIÓN DEL JUEGO
        # --------------------------------------------

        if juego_completado:

            if appid not in procesados:
                checkpoint["procesados"].append(appid)
                procesados.add(appid)

            checkpoint["progreso"][str(appid)] = {
                "cursor": cursor,
                "resenas_obtenidas": resenas_juego_actual,
                "completado": True,
                "actualizado_utc": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            print(
                f"[COMPLETADO] AppID {appid}: "
                f"{resenas_juego_actual} reseñas."
            )

        else:

            print(
                f"[PENDIENTE] AppID {appid}: "
                f"{resenas_juego_actual} reseñas."
            )

        guardar_checkpoint(checkpoint)
        guardar_resenas(checkpoint["resenas"])

        # Si Steam rechazó o falló, no seguimos con
        # los siguientes juegos.

        if detener_proceso:
            break

except KeyboardInterrupt:

    print("\n[INTERRUPCIÓN] Detenido por el usuario.")

finally:

    guardar_checkpoint(checkpoint)
    guardar_resenas(checkpoint["resenas"])

    session.close()

# ============================================================
# 12. INFORME FINAL
# ============================================================

pendientes = [
    appid for appid in appids_a_procesar
    if appid not in procesados
]

print("\n" + "=" * 65)
print("INFORME FINAL - SCRIPT 2C")
print("=" * 65)

print(f"Juegos seleccionados: {len(appids_a_procesar)}")
print(f"Juegos completados: {len(procesados)}")
print(f"Juegos pendientes: {len(pendientes)}")

print(f"Reseñas totales: {len(checkpoint['resenas'])}")
print(f"Reseñas nuevas: {resenas_nuevas}")
print(f"Errores: {errores}")

print("\nArchivos generados:")
print(RESENAS_FILE)
print(CHECKPOINT_FILE)

print("\n[FINALIZADO] Script 2C.")
