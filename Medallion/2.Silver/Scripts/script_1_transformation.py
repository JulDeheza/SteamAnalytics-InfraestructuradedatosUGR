
from pathlib import Path
import json
import pandas as pd

# ============================================================
# CONFIGURACIÓN DE RUTAS
# ============================================================

ROOT = Path("/content/Infraestructura-de-ciencia-de-datos")

BRONZE_DATA = ROOT / "Medallion" / "1.Bronze" / "Data"
SILVER_DATA = ROOT / "Medallion" / "2.Silver" / "Data"

INPUT_FILE = BRONZE_DATA / "juegos.json"
OUTPUT_FILE = SILVER_DATA / "juegos.parquet"

SILVER_DATA.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. CARGA DE BRONZE
# ============================================================

print("=" * 70)
print("SILVER - SCRIPT 1: TRANSFORMATION")
print("TRANSFORMACIÓN DEL CATÁLOGO DE JUEGOS")
print("=" * 70)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"No se encontró el archivo Bronze: {INPUT_FILE}"
    )

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    raw_data = json.load(file)

if not isinstance(raw_data, dict) or "apps" not in raw_data:
    raise ValueError("La estructura de juegos.json no es válida.")

df = pd.DataFrame(raw_data["apps"])

print("\nArchivo Bronze cargado correctamente.")
print("Registros originales:", len(df))

# ============================================================
# 2. VALIDACIÓN DE ESTRUCTURA
# ============================================================

COLUMNAS_REQUERIDAS = [
    "appid",
    "name",
    "last_modified",
    "price_change_number"
]

faltantes = [
    columna for columna in COLUMNAS_REQUERIDAS
    if columna not in df.columns
]

if faltantes:
    raise ValueError(
        f"Faltan columnas obligatorias: {faltantes}"
    )

df = df[COLUMNAS_REQUERIDAS].copy()

# ============================================================
# 3. LIMPIEZA Y NORMALIZACIÓN
# ============================================================

# APPID
df["appid"] = pd.to_numeric(
    df["appid"], errors="coerce"
)

# Nombre del juego
df["name"] = (
    df["name"]
    .astype("string")
    .str.strip()
)

# Campos numéricos
for columna in ["last_modified", "price_change_number"]:
    df[columna] = pd.to_numeric(
        df[columna], errors="coerce"
    )

# ============================================================
# 4. CONTROLES DE CALIDAD
# ============================================================

if df["appid"].isna().any():
    raise ValueError("Existen APPID nulos o inválidos.")

if df["name"].isna().any() or df["name"].eq("").any():
    raise ValueError("Existen nombres de juegos vacíos.")

if df[["last_modified", "price_change_number"]].isna().any().any():
    raise ValueError("Existen valores numéricos inválidos.")

if df["appid"].duplicated().any():
    duplicados = df.loc[
        df["appid"].duplicated(keep=False), "appid"
    ].tolist()

    raise ValueError(
        f"Se encontraron APPID duplicados: {duplicados[:10]}"
    )

# Normalización de tipos
df["appid"] = df["appid"].astype("int64")
df["last_modified"] = df["last_modified"].astype("int64")
df["price_change_number"] = df["price_change_number"].astype("int64")

# ============================================================
# 5. ORDEN Y VALIDACIÓN FINAL
# ============================================================

df = df.sort_values("appid").reset_index(drop=True)

print("\nCONTROLES DE CALIDAD")
print("-" * 70)
print("Filas finales:", len(df))
print("APPID únicos:", df["appid"].nunique())
print("APPID nulos:", df["appid"].isna().sum())
print("Nombres vacíos:", df["name"].eq("").sum())
print("Duplicados:", df["appid"].duplicated().sum())

print("\nTIPOS DE DATOS")
print(df.dtypes)

# ============================================================
# 6. EXPORTACIÓN PARQUET
# ============================================================

df.to_parquet(
    OUTPUT_FILE,
    engine="pyarrow",
    index=False
)

print("\n" + "=" * 70)
print("TRANSFORMACIÓN FINALIZADA")
print("=" * 70)
print("Archivo generado:", OUTPUT_FILE)
print("Registros exportados:", len(df))
print("Columnas:", len(df.columns))
print("\nESQUEMA FINAL")
print(df.info())
