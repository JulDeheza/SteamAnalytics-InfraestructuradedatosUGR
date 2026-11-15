
import json
import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURACIÓN DE RUTAS
# ============================================================

BASE_DIR = Path(
    "/content/Infraestructura-de-ciencia-de-datos/Medallion"
)

BRONZE_DATA_DIR = BASE_DIR / "1.Bronze" / "Data"
SILVER_DATA_DIR = BASE_DIR / "2.Silver" / "Data"

ARCHIVO_ENTRADA = BRONZE_DATA_DIR / "resenas.json"
ARCHIVO_SALIDA = SILVER_DATA_DIR / "resenas.parquet"

SILVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CAPA SILVER - SCRIPT 5: TRANSFORMACIÓN DE RESEÑAS")
print("=" * 65)

# ============================================================
# 1. CARGA DE DATOS BRONZE
# ============================================================

print("\\n1. Cargando reseñas desde Bronze...")

if not ARCHIVO_ENTRADA.exists():
    raise FileNotFoundError(
        f"No se encontró el archivo: {ARCHIVO_ENTRADA}"
    )

with open(ARCHIVO_ENTRADA, "r", encoding="utf-8") as archivo:
    data = json.load(archivo)

if not isinstance(data, list):
    raise TypeError(
        "La estructura de resenas.json debe ser una lista."
    )

if not data:
    raise ValueError("El archivo de reseñas está vacío.")

# Normalizar estructuras anidadas
df = pd.json_normalize(data, sep=".")

filas_originales = len(df)

print(f"Reseñas cargadas: {filas_originales:,}")

# ============================================================
# 2. VALIDACIÓN DE COLUMNAS
# ============================================================

print("\\n2. Validando estructura...")

columnas_obligatorias = [
    "recommendationid",
    "appid",
    "steamid"
]

for columna in columnas_obligatorias:
    if columna not in df.columns:
        raise ValueError(
            f"Falta la columna obligatoria: {columna}"
        )

# ============================================================
# 3. NORMALIZACIÓN DE IDENTIFICADORES
# ============================================================

print("\\n3. Normalizando identificadores...")

# SteamID como texto para evitar pérdida de precisión
df["steamid"] = (
    df["steamid"]
    .astype("string")
    .str.strip()
)

# APPID como entero nullable
df["appid"] = pd.to_numeric(
    df["appid"],
    errors="coerce"
).astype("Int64")

# RecommendationID como texto
df["recommendationid"] = (
    df["recommendationid"]
    .astype("string")
    .str.strip()
)

# Validar identificadores obligatorios
for columna in columnas_obligatorias:

    if df[columna].isna().any():
        raise ValueError(
            f"Se encontraron valores nulos en {columna}."
        )

    if (df[columna] == "").any():
        raise ValueError(
            f"Se encontraron valores vacíos en {columna}."
        )

# Validar duplicados
if df["recommendationid"].duplicated().any():
    raise ValueError(
        "Se encontraron recommendationid duplicados."
    )

print(f"RecommendationID únicos: {df['recommendationid'].nunique():,}")
print(f"SteamID únicos: {df['steamid'].nunique():,}")
print(f"APPID únicos: {df['appid'].nunique():,}")

# ============================================================
# 4. VALIDACIÓN DE IDENTIFICADOR DEL AUTOR
# ============================================================

print("\\n4. Validando identificadores del autor...")

# author.steamid es redundante con steamid.
# Antes de eliminarlo, verificar que no existan discrepancias.

if "author.steamid" in df.columns:

    autor = (
        df["author.steamid"]
        .astype("string")
        .str.strip()
    )

    mascara_comparacion = autor.notna() & df["steamid"].notna()

    discrepancias = (
        autor[mascara_comparacion]
        != df.loc[mascara_comparacion, "steamid"]
    ).sum()

    if discrepancias > 0:
        raise ValueError(
            f"Se encontraron {discrepancias} diferencias entre "
            "steamid y author.steamid. No se elimina la columna."
        )

    df = df.drop(columns=["author.steamid"])

    print("author.steamid validado y retirado por redundancia.")

else:
    print("No existe author.steamid. Se continúa.")

# ============================================================
# 5. TRANSFORMACIÓN DE FECHAS 
# ============================================================

print("\\n5. Transformando fechas Unix...")

import math
from datetime import datetime, timezone

columnas_fecha = [
    "timestamp_created",
    "timestamp_updated",
    "author.last_played",
    "timestamp_dev_responded"
]

for columna in columnas_fecha:

    if columna in df.columns:

        # Convertir a valores numéricos
        valores = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

        # Conservar los timestamps numéricos originales
        df[columna] = valores

        # Convertir individualmente, evitando desbordamientos
        fechas_convertidas = []

        for valor in valores:

            if pd.isna(valor):
                fechas_convertidas.append(pd.NaT)
                continue

            try:
                numero = float(valor)

                # Validar rango razonable: Unix seconds
                if (
                    not math.isfinite(numero)
                    or numero <= 0
                    or numero >= 3_000_000_000
                ):
                    fechas_convertidas.append(pd.NaT)
                    continue

                fecha = datetime.fromtimestamp(
                    int(numero),
                    tz=timezone.utc
                )

                fechas_convertidas.append(fecha)

            except (ValueError, OverflowError, OSError):
                fechas_convertidas.append(pd.NaT)

        # Crear columna datetime en UTC
        df[f"{columna}_parsed"] = pd.Series(
            fechas_convertidas,
            index=df.index,
            dtype="datetime64[ns, UTC]"
        )

        print(
            f"{columna}: "
            f"{df[f'{columna}_parsed'].notna().sum():,} "
            "fechas válidas"
        )
# ============================================================
# 6. NORMALIZACIÓN DE CAMPOS NUMÉRICOS
# ============================================================

print("\\n6. Normalizando campos numéricos...")

columnas_numericas = [
    "votes_up",
    "votes_funny",
    "comment_count",
    "author.num_reviews",
    "author.playtime_forever",
    "author.playtime_last_two_weeks",
    "author.playtime_at_review",
    "author.deck_playtime_at_review",
    "hardware.system_ram",
    "hardware.vram_size"
]

for columna in columnas_numericas:

    if columna in df.columns:

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

# ============================================================
# 7. NORMALIZACIÓN DE CAMPOS BOOLEANOS
# ============================================================

print("\\n7. Normalizando campos booleanos...")

columnas_booleanas = [
    "voted_up",
    "steam_purchase",
    "received_for_free",
    "written_during_early_access",
    "primarily_steam_deck",
    "refunded"
]

for columna in columnas_booleanas:

    if columna in df.columns:

        valores = df[columna]

        valores_texto = valores.astype("string").str.lower()

        df[columna] = valores_texto.map({
            "true": True,
            "false": False,
            "1": True,
            "0": False
        }).astype("boolean")

# ============================================================
# 8. VALIDACIÓN DE INTEGRIDAD
# ============================================================

print("\\n8. Validando integridad...")

if len(df) != filas_originales:
    raise ValueError(
        "La cantidad de reseñas cambió durante la transformación."
    )

if df["recommendationid"].isna().any():
    raise ValueError("Existen recommendationid nulos.")

if df["recommendationid"].duplicated().any():
    raise ValueError("Existen recommendationid duplicados.")

if df["steamid"].isna().any():
    raise ValueError("Existen SteamID nulos.")

if df["appid"].isna().any():
    raise ValueError("Existen APPID nulos.")

# ============================================================
# 9. ORDENAMIENTO
# ============================================================

df = df.sort_values(
    by="recommendationid",
    ascending=True
).reset_index(drop=True)

# ============================================================
# 10. EXPORTACIÓN A PARQUET
# ============================================================

print("\\n9. Exportando reseñas a Parquet...")

df.to_parquet(
    ARCHIVO_SALIDA,
    engine="pyarrow",
    index=False
)

# ============================================================
# 11. VERIFICACIÓN DE EXPORTACIÓN
# ============================================================

print("\\n10. Verificando archivo exportado...")

df_verificacion = pd.read_parquet(ARCHIVO_SALIDA)

if len(df_verificacion) != filas_originales:
    raise ValueError(
        "La cantidad de filas del Parquet no coincide con Bronze."
    )

if df_verificacion["recommendationid"].duplicated().any():
    raise ValueError(
        "El Parquet contiene recommendationid duplicados."
    )

if df_verificacion["steamid"].isna().any():
    raise ValueError(
        "El Parquet contiene SteamID nulos."
    )

if df_verificacion["appid"].isna().any():
    raise ValueError(
        "El Parquet contiene APPID nulos."
    )

# ============================================================
# 12. INFORME FINAL
# ============================================================

tamano_mb = ARCHIVO_SALIDA.stat().st_size / (1024 ** 2)

print("\\n" + "=" * 65)
print("RESULTADO - SCRIPT 5")
print("=" * 65)

print(f"Reseñas originales: {filas_originales:,}")
print(f"Reseñas Silver: {len(df_verificacion):,}")
print(f"Columnas: {len(df_verificacion.columns)}")
print(
    "RecommendationID únicos:",
    f"{df_verificacion['recommendationid'].nunique():,}"
)
print(
    "SteamID únicos:",
    f"{df_verificacion['steamid'].nunique():,}"
)
print(
    "APPID únicos:",
    f"{df_verificacion['appid'].nunique():,}"
)
print(f"Tamaño del archivo: {tamano_mb:.2f} MB")

print("\\nColumnas exportadas:")

for columna in df_verificacion.columns:
    print(f"- {columna}: {df_verificacion[columna].dtype}")

print("\\nArchivo generado:")
print(ARCHIVO_SALIDA)

print("\\nSCRIPT 5 FINALIZADO CORRECTAMENTE.")
