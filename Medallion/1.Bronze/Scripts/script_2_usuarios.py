"""
╔══════════════════════════════════════════════════════════════╗
║  CAPA BRONZE — Script 2: Usuarios (usuarios.json)            ║
║  Arquitectura Medallion · Ingesta cruda desde Steam API      ║
║  Para ejecutar en Google Colab                               ║
╚══════════════════════════════════════════════════════════════╝

Descripción:
  Recibe una lista de Steam IDs y extrae la información de perfil
  de cada jugador usando GetPlayerSummaries. Filtra/flaggea los
  jugadores cuya cuenta fue creada o cuya última conexión cayó
  entre el 01/01/2020 y el 31/12/2025.

Endpoint utilizado:
  - ISteamUser/GetPlayerSummaries/v0002 (requiere API key)
    Ref: https://developer.valvesoftware.com/wiki/Steam_Web_API#GetPlayerSummaries_.28v0001.29
"""

# ============================================================
# IMPORTS
# ============================================================
import json
import time
import datetime
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from google.colab import userdata

# ============================================================
# SEGURIDAD — API Key desde Colab Secrets
# ============================================================
API_KEY = userdata.get('STEAM_API_KEY')

# ============================================================
# CONFIGURACIÓN — Cambiar a False para ejecución completa
# ============================================================
TEST_MODE = True

# ────────────────────────────────────────────────────────────
# LISTA DE STEAM IDs
# ────────────────────────────────────────────────────────────
# Instrucciones:
#   ▸ steam_ids_test   → 2-5 IDs para modo prueba
#   ▸ steam_ids_prod   → tu lista completa para producción
#
# Los IDs deben ser strings de 17 dígitos (SteamID64).
# Puedes obtenerlos de steamid.io o de tu propia base de datos.
# ────────────────────────────────────────────────────────────
steam_ids_test = [
    "76561198000000001",
    "76561198000000002",
    "76561198000000003",
]

steam_ids_prod = [
    # TODO: Colocar aquí tu lista completa de Steam IDs para producción.
    # Ejemplo:
    # "76561198000000001",
    # "76561198000000002",
    # ...
]

STEAM_IDS = steam_ids_test if TEST_MODE else steam_ids_prod

# Tamaño de lote — GetPlayerSummaries acepta hasta 100 IDs por request
BATCH_SIZE = 100
SLEEP_ENTRE_LOTES = 1.5  # Segundos entre cada lote

# ============================================================
# FILTRO TEMPORAL — Rango 2020-2025 en UNIX timestamps
# ============================================================
FECHA_INICIO = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
FECHA_FIN    = datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
TS_INICIO    = int(FECHA_INICIO.timestamp())   # 1577836800
TS_FIN       = int(FECHA_FIN.timestamp())       # 1767225599

# ============================================================
# SESIÓN HTTP RESILIENTE
# ============================================================
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
session.mount("https://", HTTPAdapter(max_retries=retries))

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ts_en_rango(ts: int | None) -> bool:
    """Verifica si un UNIX timestamp cae dentro del rango 2020-2025."""
    if ts is None:
        return False
    return TS_INICIO <= ts <= TS_FIN


def dividir_en_lotes(lista: list, tam: int):
    """Generador que divide una lista en sub-listas de tamaño `tam`."""
    for i in range(0, len(lista), tam):
        yield lista[i : i + tam]


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
print(f"[Usuarios] Modo: {'PRUEBA' if TEST_MODE else 'PRODUCCIÓN'}")
print(f"[Usuarios] IDs a consultar: {len(STEAM_IDS)}")
start_time = time.time()

usuarios_bronze = []
errores = 0
total_obtenidos = 0  # Jugadores devueltos por la API (antes de filtrar)

lotes = list(dividir_en_lotes(STEAM_IDS, BATCH_SIZE))
total_lotes = len(lotes)

print(f"[Usuarios] Se procesarán {total_lotes} lote(s) de hasta {BATCH_SIZE} IDs.\n")

for num_lote, lote in enumerate(lotes, start=1):
    ids_csv = ",".join(lote)

    try:
        print(f"[Usuarios] Procesando lote {num_lote}/{total_lotes} ({len(lote)} IDs)...")
        resp = session.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
            params={"key": API_KEY, "steamids": ids_csv},
            timeout=20,
        )
        resp.raise_for_status()
        jugadores = resp.json().get("response", {}).get("players", [])
        total_obtenidos += len(jugadores)

        en_rango_lote = 0
        for jugador in jugadores:
            timecreated = jugador.get("timecreated")
            lastlogoff  = jugador.get("lastlogoff")

            cumple_timecreated = ts_en_rango(timecreated)
            cumple_lastlogoff  = ts_en_rango(lastlogoff)

            # Guardar si al menos uno de los dos campos cae en rango
            if cumple_timecreated or cumple_lastlogoff:
                jugador["_bronze_meta"] = {
                    "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source": "steam_player_summaries_api",
                    "filtro_temporal": {
                        "cumple_timecreated": cumple_timecreated,
                        "cumple_lastlogoff": cumple_lastlogoff,
                    },
                    "timecreated_legible": (
                        datetime.datetime.fromtimestamp(timecreated, tz=datetime.timezone.utc).isoformat()
                        if timecreated else None
                    ),
                    "lastlogoff_legible": (
                        datetime.datetime.fromtimestamp(lastlogoff, tz=datetime.timezone.utc).isoformat()
                        if lastlogoff else None
                    ),
                }
                usuarios_bronze.append(jugador)
                en_rango_lote += 1

        print(f"[Usuarios] Lote {num_lote}: {len(jugadores)} jugadores obtenidos, "
              f"{en_rango_lote} en rango temporal 2020-2025")

    except Exception as e:
        errores += 1
        print(f"[Usuarios][ERROR] Lote {num_lote}: {e}")

    # Respetar rate limits entre lotes
    if num_lote < total_lotes:
        time.sleep(SLEEP_ENTRE_LOTES)

# ============================================================
# GUARDAR RESULTADO — JSON crudo (Bronze)
# ============================================================
with open("usuarios.json", "w", encoding="utf-8") as f:
    json.dump(usuarios_bronze, f, ensure_ascii=False, indent=2)

# ============================================================
# RESUMEN FINAL
# ============================================================
elapsed = time.time() - start_time

print(f"\n{'='*60}")
print(f"[Usuarios] RESUMEN BRONZE")
print(f"{'='*60}")
print(f"  Modo:                {'PRUEBA' if TEST_MODE else 'PRODUCCIÓN'}")
print(f"  IDs consultados:     {len(STEAM_IDS)}")
print(f"  Jugadores obtenidos: {total_obtenidos}")
print(f"  En rango temporal:   {len(usuarios_bronze)}")
print(f"  Errores de lote:     {errores}")
print(f"  Archivo:             usuarios.json")
print(f"  Tiempo ejecución:    {elapsed:.1f}s")
print(f"{'='*60}")
