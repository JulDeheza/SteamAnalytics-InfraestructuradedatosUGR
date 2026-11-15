# ============================================================
# CAPA BRONZE — SCRIPT 2A: DESCUBRIMIENTO DE STEAM IDS
# Lee 'resenas.json' para extraer autores únicos y guardarlos
# ============================================================
import os
import json
from pathlib import Path

BASE_DIR = Path("/content/Infraestructura-de-ciencia-de-datos/Medallion/1.Bronze/Data")
RESENAS_FILE = BASE_DIR / "resenas.json"
STEAM_IDS_FILE = BASE_DIR / "steam_ids.json"

print("=== SCRIPT 2A: EXTRACCIÓN DE AUTORES ÚNICOS ===")

if RESENAS_FILE.exists():
    print(f"📖 Leyendo reseñas desde: {RESENAS_FILE.name}...")
    with open(RESENAS_FILE, "r", encoding="utf-8") as f:
        resenas = json.load(f)

    # Extraer identificadores estructurados únicos (de 17 caracteres numéricos)
    steam_ids_autores = set()
    for r in resenas:
        sid = str(r.get("steamid", "")).strip()
        if sid.isdigit() and len(sid) == 17:
            steam_ids_autores.add(sid)

    steam_ids_lista = sorted(list(steam_ids_autores))
    print(f"🎯 Se identificaron {len(steam_ids_lista):,} autores únicos reales.")

    # Guardar en steam_ids.json
    with open(STEAM_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump({"steamids": steam_ids_lista}, f, indent=2)
    print(f"✅ Archivo {STEAM_IDS_FILE.name} guardado con éxito en: {BASE_DIR}")
else:
    print(f"❌ Error: No se encontró el archivo de origen '{RESENAS_FILE.name}'.")