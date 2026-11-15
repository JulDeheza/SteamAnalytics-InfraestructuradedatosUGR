
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

ARCHIVO_ENTRADA = BRONZE_DATA_DIR / "novedades.json"
ARCHIVO_JUEGOS = SILVER_DATA_DIR / "juegos.parquet"

ARCHIVO_SALIDA = SILVER_DATA_DIR / "novedades.parquet"
ARCHIVO_ENRIQUECIDO = SILVER_DATA_DIR / "novedades_juegos.parquet"

SILVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CAPA SILVER - SCRIPT 3: TRANSFORMACIÓN DE NOVEDADES")
print("=" * 65)

# ============================================================
# 1. CARGA DE NOVEDADES
# ============================================================

print("\\n1. Cargando novedades desde Bronze...")

if not ARCHIVO_ENTRADA.exists():
    raise FileNotFoundError(
        f"No se encontró: {ARCHIVO_ENTRADA}"
    )

with open(ARCHIVO_ENTRADA, "r", encoding="utf-8") as archivo:
    data = json.load(archivo)

if not isinstance(data, list):
    raise TypeError(
        "La estructura de novedades.json debe ser una lista."
    )

df = pd.json_normalize(data, sep=".")

if df.empty:
    raise ValueError("No se encontraron novedades.")

filas_originales = len(df)

print(f"Novedades cargadas: {filas_originales:,}")

# ============================================================
# 2. VALIDACIÓN DE ESTRUCTURA
# ============================================================

print("\\n2. Validando estructura...")

columnas_obligatorias = [
    "gid",
    "title",
    "date"
]

for columna in columnas_obligatorias:
    if columna not in df.columns:
        raise ValueError(
            f"Falta la columna obligatoria: {columna}"
        )

# ============================================================
# 3. NORMALIZACIÓN DE APPID
# ============================================================

print("\\n3. Normalizando identificadores de juegos...")

# Recuperar APPID desde metadata si está disponible
if "_bronze_meta" in df.columns:

    df["appid_meta"] = df["_bronze_meta"].apply(
        lambda x: x.get("appid")
        if isinstance(x, dict)
        else None
    )

    if "appid" not in df.columns:
        df["appid"] = pd.NA
    else:
        df["appid"] = df["appid"].replace("", pd.NA)

    df["appid"] = df["appid"].fillna(df["appid_meta"])

elif "appid" not in df.columns:
    df["appid"] = pd.NA

# Conversión numérica conservando faltantes
df["appid"] = pd.to_numeric(
    df["appid"],
    errors="coerce"
).astype("Int64")

# No eliminar novedades por APPID faltante
print(
    "Novedades con APPID válido:",
    f"{df['appid'].notna().sum():,}"
)

print(
    "Novedades sin APPID válido:",
    f"{df['appid'].isna().sum():,}"
)

# ============================================================
# 4. NORMALIZACIÓN DE FECHAS
# ============================================================

print("\\n4. Transformando fechas...")

df["date_numeric"] = pd.to_numeric(
    df["date"],
    errors="coerce"
)

df["date_parsed"] = pd.to_datetime(
    df["date_numeric"],
    unit="s",
    errors="coerce",
    utc=True
)

df["year"] = df["date_parsed"].dt.year.astype("Int64")

fechas_validas = df["date_parsed"].notna().sum()
fechas_invalidas = df["date_parsed"].isna().sum()

print(f"Fechas válidas: {fechas_validas:,}")
print(f"Fechas inválidas o nulas: {fechas_invalidas:,}")

# ============================================================
# 5. NORMALIZACIÓN DE TEXTOS
# ============================================================

print("\\n5. Normalizando campos de texto...")

if "title" in df.columns:
    df["title"] = (
        df["title"]
        .fillna("Sin título")
        .astype("string")
        .str.strip()
    )

if "gid" in df.columns:
    df["gid"] = df["gid"].astype("string").str.strip()

# ============================================================
# 6. VALIDACIÓN DE GID
# ============================================================

print("\\n6. Validando identificadores de novedades...")

if df["gid"].isna().any() or (df["gid"] == "").any():
    raise ValueError(
        "Se encontraron GID nulos o vacíos."
    )

if df["gid"].duplicated().any():
    raise ValueError(
        "Se encontraron GID duplicados."
    )

# ============================================================
# 7. EXPORTACIÓN DE NOVEDADES
# ============================================================

print("\\n7. Exportando novedades.parquet...")

df.to_parquet(
    ARCHIVO_SALIDA,
    engine="pyarrow",
    index=False
)

# ============================================================
# 8. ENRIQUECIMIENTO CON JUEGOS
# ============================================================

print("\\n8. Enriqueciendo novedades con catálogo de juegos...")

if not ARCHIVO_JUEGOS.exists():
    raise FileNotFoundError(
        "No se encontró juegos.parquet. "
        "Ejecutá primero el Script 1."
    )

df_juegos = pd.read_parquet(ARCHIVO_JUEGOS)

if not {"appid", "name"}.issubset(df_juegos.columns):
    raise ValueError(
        "juegos.parquet no contiene appid y name."
    )

# Preparar catálogo
df_juegos = df_juegos[["appid", "name"]].copy()

df_juegos["appid"] = pd.to_numeric(
    df_juegos["appid"],
    errors="coerce"
).astype("Int64")

if df_juegos["appid"].isna().any():
    raise ValueError(
        "El catálogo de juegos contiene APPID nulos."
    )

if df_juegos["appid"].duplicated().any():
    raise ValueError(
        "El catálogo de juegos contiene APPID duplicados."
    )

# Renombrar antes del JOIN
df_juegos = df_juegos.rename(
    columns={"name": "game_name"}
)

# Enriquecer mediante LEFT JOIN
df_enriquecido = df.merge(
    df_juegos,
    on="appid",
    how="left",
    validate="many_to_one"
)

# ============================================================
# 9. VALIDACIÓN DE INTEGRIDAD
# ============================================================

print("\\n9. Validando resultados...")

if len(df_enriquecido) != filas_originales:
    raise ValueError(
        "El JOIN modificó la cantidad de novedades."
    )

if df_enriquecido["gid"].duplicated().any():
    raise ValueError(
        "Se detectaron GID duplicados después del JOIN."
    )

juegos_encontrados = df_enriquecido["game_name"].notna().sum()
juegos_no_encontrados = df_enriquecido["game_name"].isna().sum()

print(f"Juegos asociados: {juegos_encontrados:,}")
print(f"Juegos no encontrados: {juegos_no_encontrados:,}")

# ============================================================
# 10. EXPORTACIÓN ENRIQUECIDA
# ============================================================

print("\\n10. Exportando novedades_juegos.parquet...")

df_enriquecido.to_parquet(
    ARCHIVO_ENRIQUECIDO,
    engine="pyarrow",
    index=False
)

# ============================================================
# 11. VERIFICACIÓN DE ARCHIVOS
# ============================================================

df_verificacion = pd.read_parquet(ARCHIVO_SALIDA)
df_verificacion_enriquecido = pd.read_parquet(
    ARCHIVO_ENRIQUECIDO
)

if len(df_verificacion) != filas_originales:
    raise ValueError(
        "La exportación de novedades no coincide."
    )

if len(df_verificacion_enriquecido) != filas_originales:
    raise ValueError(
        "La exportación enriquecida no coincide."
    )

# ============================================================
# 12. INFORME FINAL
# ============================================================

print("\\n" + "=" * 65)
print("RESULTADO - SCRIPT 3")
print("=" * 65)

print(f"Novedades originales: {filas_originales:,}")
print(f"Novedades Silver: {len(df_verificacion):,}")
print(f"GID únicos: {df_verificacion['gid'].nunique():,}")
print(f"Juegos asociados: {juegos_encontrados:,}")
print(f"Juegos no encontrados: {juegos_no_encontrados:,}")

print("\\nArchivos generados:")
print(ARCHIVO_SALIDA)
print(ARCHIVO_ENRIQUECIDO)

print("\\nSCRIPT 3 FINALIZADO CORRECTAMENTE.")
