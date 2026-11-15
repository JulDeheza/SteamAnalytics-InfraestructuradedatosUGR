
import pandas as pd
from pathlib import Path

# ============================================================
# GOLD - SCRIPT 3: CONSTRUCCIÓN FACT NOVEDADES
# Granularidad: una fila por GID
# ============================================================

BASE = Path(
    "/content/Infraestructura-de-ciencia-de-datos/Medallion"
)

SILVER_DATA = BASE / "2.Silver" / "Data"
GOLD_DATA = BASE / "3.Gold" / "Data"

ARCHIVOS = {
    "novedades": SILVER_DATA / "novedades_consolidadas.parquet",
    "juegos": GOLD_DATA / "dim_juegos.parquet",
    "fechas": GOLD_DATA / "dim_fecha.parquet"
}

SALIDA = GOLD_DATA / "fact_novedades.parquet"


# ------------------------------------------------------------
# 1. CARGA DE ARCHIVOS
# ------------------------------------------------------------

print("=" * 70)
print("GOLD - SCRIPT 3: CONSTRUCCIÓN FACT NOVEDADES")
print("=" * 70)

for nombre, ruta in ARCHIVOS.items():
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo {nombre}: {ruta}"
        )

novedades = pd.read_parquet(ARCHIVOS["novedades"])
juegos = pd.read_parquet(ARCHIVOS["juegos"])
fechas = pd.read_parquet(ARCHIVOS["fechas"])

print("\n1. ARCHIVOS CARGADOS")
print("Novedades:", len(novedades))
print("Juegos:", len(juegos))
print("Fechas:", len(fechas))


# ------------------------------------------------------------
# 2. VALIDAR ESTRUCTURAS
# ------------------------------------------------------------

columnas_requeridas = {
    "novedades": ["gid", "appid", "date_parsed"],
    "juegos": ["game_key", "appid"],
    "fechas": ["date_key", "date"]
}

for nombre, columnas in columnas_requeridas.items():

    df = {
        "novedades": novedades,
        "juegos": juegos,
        "fechas": fechas
    }[nombre]

    faltantes = set(columnas) - set(df.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {nombre}: {faltantes}"
        )

if novedades["gid"].isna().any():
    raise ValueError("Existen GID nulos en novedades.")

if novedades["gid"].duplicated().any():
    raise ValueError("Existen GID duplicados en novedades.")

if juegos["appid"].dropna().duplicated().any():
    raise ValueError("APPID duplicados en dim_juegos.")

if fechas["date_key"].duplicated().any():
    raise ValueError("date_key duplicados en dim_fecha.")

print("\n2. ESTRUCTURAS VALIDADAS")


# ------------------------------------------------------------
# 3. PREPARAR CLAVES NATURALES
# ------------------------------------------------------------

novedades["appid"] = pd.to_numeric(
    novedades["appid"], errors="coerce"
).astype("Int64")

juegos["appid"] = pd.to_numeric(
    juegos["appid"], errors="coerce"
).astype("Int64")

novedades["_fecha"] = pd.to_datetime(
    novedades["date_parsed"],
    errors="coerce",
    utc=True
).dt.tz_convert(None).dt.normalize()

novedades["_date_key"] = (
    novedades["_fecha"].dt.strftime("%Y%m%d")
)

novedades["_date_key"] = pd.to_numeric(
    novedades["_date_key"], errors="coerce"
).fillna(0).astype("int64")

print("Claves naturales preparadas.")


# ------------------------------------------------------------
# 4. ASOCIAR JUEGOS
# ------------------------------------------------------------

mapa_juegos = juegos[
    ["appid", "game_key"]
].copy()

fact = novedades.merge(
    mapa_juegos,
    on="appid",
    how="left",
    validate="many_to_one"
)

juegos_sin_match = fact["game_key"].isna().sum()

fact["game_key"] = (
    fact["game_key"].fillna(0).astype("int64")
)

print("\n4. ASOCIACIÓN DE JUEGOS")
print("Novedades sin juego asociado:", juegos_sin_match)
print(
    "Asignadas a game_key = 0:",
    (fact["game_key"] == 0).sum()
)


# ------------------------------------------------------------
# 5. ASOCIAR FECHAS
# ------------------------------------------------------------

mapa_fechas = fechas[
    ["date_key"]
].copy()

claves_fecha = set(
    mapa_fechas["date_key"].astype("int64")
)

fact["date_key"] = fact["_date_key"].where(
    fact["_date_key"].isin(claves_fecha),
    0
).astype("int64")

fechas_sin_match = (fact["date_key"] == 0).sum()

print("\n5. ASOCIACIÓN DE FECHAS")
print("Novedades sin fecha asociada:", fechas_sin_match)
print(
    "Asignadas a date_key = 0:",
    fechas_sin_match
)


# ------------------------------------------------------------
# 6. CONSTRUIR TABLA DE HECHOS
# ------------------------------------------------------------

columnas_fact = [
    "gid",
    "game_key",
    "date_key",
    "appid",
    "title",
    "url",
    "is_external_url",
    "author",
    "feedlabel",
    "feedname",
    "feed_type",
    "date",
    "year",
    "tags"
]

columnas_disponibles = [
    c for c in columnas_fact if c in fact.columns
]

fact = fact[columnas_disponibles].copy()

# Renombrar atributos para mayor claridad
fact = fact.rename(columns={
    "date": "timestamp_publicacion",
    "year": "year_publicacion",
    "feedlabel": "feed_label",
    "feedname": "feed_name",
    "feed_type": "feed_type"
})

fact["game_key"] = fact["game_key"].astype("int64")
fact["date_key"] = fact["date_key"].astype("int64")

print("\n6. TABLA FACT CONSTRUIDA")


# ------------------------------------------------------------
# 7. VALIDACIÓN FINAL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDACIÓN FINAL - FACT_NOVEDADES")
print("=" * 70)

errores = []

if len(fact) != len(novedades):
    errores.append("La cantidad de filas no coincide con Silver.")

if fact["gid"].isna().any():
    errores.append("Existen GID nulos.")

if fact["gid"].duplicated().any():
    errores.append("Existen GID duplicados.")

for columna in ["game_key", "date_key"]:
    if fact[columna].isna().any():
        errores.append(f"Existen nulos en {columna}.")

    if (fact[columna] < 0).any():
        errores.append(f"Existen claves negativas en {columna}.")

# Comprobar integridad referencial
claves_juegos = set(juegos["game_key"].astype("int64"))
claves_fechas = set(fechas["date_key"].astype("int64"))

if not set(fact["game_key"]).issubset(claves_juegos):
    errores.append("Hay game_key inexistentes en dim_juegos.")

if not set(fact["date_key"]).issubset(claves_fechas):
    errores.append("Hay date_key inexistentes en dim_fecha.")

if errores:
    for error in errores:
        print("ERROR:", error)

    raise ValueError(
        "La validación de fact_novedades no fue aprobada."
    )

print("OK: Cantidad de filas conservada.")
print("OK: GID sin nulos.")
print("OK: GID sin duplicados.")
print("OK: Claves sustitutas válidas.")
print("OK: Integridad referencial.")
    

# ------------------------------------------------------------
# 8. EXPORTAR
# ------------------------------------------------------------

SALIDA.parent.mkdir(parents=True, exist_ok=True)

fact.to_parquet(
    SALIDA,
    index=False
)

print("\n" + "=" * 70)
print("RESUMEN FACT_NOVEDADES")
print("=" * 70)

print("Total de novedades:", len(fact))
print("Columnas:", len(fact.columns))
print("Juegos sin asociación:", juegos_sin_match)
print("Fechas sin asociación:", fechas_sin_match)
print("Archivo generado:", SALIDA)

print("\nGOLD - SCRIPT 3 COMPLETADO CORRECTAMENTE")
