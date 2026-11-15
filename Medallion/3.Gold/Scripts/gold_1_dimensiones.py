
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# GOLD - SCRIPT 1: CONSTRUCCIÓN DE DIMENSIONES
# ============================================================

ROOT = Path(
    "/content/Infraestructura-de-ciencia-de-datos"
)

SILVER = ROOT / "Medallion" / "2.Silver" / "Data"
OUTPUT = ROOT / "Medallion" / "3.Gold" / "Data"

OUTPUT.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("GOLD - SCRIPT 1: CONSTRUCCIÓN DE DIMENSIONES")
print("=" * 70)


# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------

def cargar_parquet(nombre):

    ruta = SILVER / nombre

    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró: {ruta}"
        )

    df = pd.read_parquet(ruta)

    print(
        f"Cargado: {nombre} | Filas: {len(df):,}"
    )

    return df


def guardar_parquet(df, nombre):

    ruta = OUTPUT / nombre

    df.to_parquet(
        ruta,
        index=False
    )

    print(
        f"Guardado: {nombre} | "
        f"Filas: {len(df):,} | "
        f"Columnas: {len(df.columns)}"
    )


def agregar_unknown(df, clave, valores):

    registro = {}

    for columna in df.columns:

        if columna == clave:
            registro[columna] = 0

        elif columna in valores:
            registro[columna] = valores[columna]

        else:
            registro[columna] = pd.NA

    registro_df = pd.DataFrame(
        [registro],
        columns=df.columns
    )

    resultado = pd.concat(
        [registro_df, df],
        ignore_index=True
    )

    resultado[clave] = (
        pd.to_numeric(
            resultado[clave],
            errors="raise"
        ).astype("int64")
    )

    return resultado


# ------------------------------------------------------------
# 1. DIM_USUARIOS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("1. DIMENSIÓN USUARIOS")
print("=" * 70)

usuarios = cargar_parquet("usuarios.parquet")

if "steamid" not in usuarios.columns:
    raise ValueError("No existe steamid.")

usuarios["steamid"] = (
    usuarios["steamid"]
    .astype("string")
    .str.strip()
)

usuarios = usuarios.dropna(
    subset=["steamid"]
).copy()

usuarios = usuarios[
    usuarios["steamid"] != ""
].copy()

if usuarios["steamid"].duplicated().any():
    raise ValueError("SteamID duplicados.")

dim_usuarios = usuarios.copy()

dim_usuarios.insert(
    0,
    "user_key",
    np.arange(1, len(dim_usuarios) + 1)
)

# Fecha de creación
if "timecreated_parsed" in dim_usuarios.columns:

    dim_usuarios["account_created_at"] = (
        pd.to_datetime(
            dim_usuarios["timecreated_parsed"],
            utc=True,
            errors="coerce"
        )
    )

elif "timecreated" in dim_usuarios.columns:

    numeric = pd.to_numeric(
        dim_usuarios["timecreated"],
        errors="coerce"
    )

    dim_usuarios["account_created_at"] = (
        pd.to_datetime(
            numeric,
            unit="s",
            utc=True,
            errors="coerce"
        )
    )

else:

    dim_usuarios["account_created_at"] = pd.NaT

dim_usuarios["account_created_year"] = (
    dim_usuarios["account_created_at"]
    .dt.year
    .astype("Int64")
)

dim_usuarios = agregar_unknown(
    dim_usuarios,
    "user_key",
    {"steamid": "UNKNOWN"}
)

guardar_parquet(
    dim_usuarios,
    "dim_usuarios.parquet"
)


# ------------------------------------------------------------
# 2. DIM_JUEGOS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("2. DIMENSIÓN JUEGOS")
print("=" * 70)

juegos = cargar_parquet("juegos.parquet")

if not {"appid", "name"}.issubset(juegos.columns):
    raise ValueError(
        "Faltan appid o name en juegos."
    )

juegos["appid"] = pd.to_numeric(
    juegos["appid"],
    errors="coerce"
).astype("Int64")

juegos = juegos.dropna(
    subset=["appid"]
).copy()

if juegos["appid"].duplicated().any():
    raise ValueError("APPID duplicados.")

dim_juegos = juegos.copy()

dim_juegos.insert(
    0,
    "game_key",
    np.arange(1, len(dim_juegos) + 1)
)

dim_juegos = agregar_unknown(
    dim_juegos,
    "game_key",
    {"name": "UNKNOWN"}
)

guardar_parquet(
    dim_juegos,
    "dim_juegos.parquet"
)


# ------------------------------------------------------------
# 3. DIM_FECHA
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("3. DIMENSIÓN FECHA")
print("=" * 70)

resenas = cargar_parquet("resenas.parquet")
novedades = cargar_parquet("novedades.parquet")

fechas = []

# Fechas de reseñas
if "timestamp_created" not in resenas.columns:
    raise ValueError(
        "Falta timestamp_created en reseñas."
    )

fechas_resenas = pd.to_datetime(
    resenas["timestamp_created"],
    utc=True,
    errors="coerce"
).dropna().dt.normalize()

fechas.extend(fechas_resenas.tolist())

# Fechas de novedades
if "date_parsed" in novedades.columns:

    fechas_novedades = pd.to_datetime(
        novedades["date_parsed"],
        utc=True,
        errors="coerce"
    ).dropna().dt.normalize()

    fechas.extend(fechas_novedades.tolist())

# Fechas de creación de usuarios
if "timecreated_parsed" in usuarios.columns:

    fechas_usuarios = pd.to_datetime(
        usuarios["timecreated_parsed"],
        utc=True,
        errors="coerce"
    ).dropna().dt.normalize()

    fechas.extend(fechas_usuarios.tolist())

fechas_unicas = sorted(set(fechas))

if not fechas_unicas:
    raise ValueError("No hay fechas válidas.")

dim_fecha = pd.DataFrame({
    "date": pd.to_datetime(
        fechas_unicas,
        utc=True
    )
})

dim_fecha["date_key"] = (
    dim_fecha["date"]
    .dt.strftime("%Y%m%d")
    .astype("int64")
)

dim_fecha["year"] = (
    dim_fecha["date"].dt.year.astype("int64")
)

dim_fecha["quarter"] = (
    dim_fecha["date"].dt.quarter.astype("int64")
)

dim_fecha["month"] = (
    dim_fecha["date"].dt.month.astype("int64")
)

dim_fecha["month_name"] = (
    dim_fecha["date"].dt.month_name()
)

dim_fecha["day"] = (
    dim_fecha["date"].dt.day.astype("int64")
)

dim_fecha["day_of_week"] = (
    dim_fecha["date"].dt.dayofweek + 1
).astype("int64")

dim_fecha["day_name"] = (
    dim_fecha["date"].dt.day_name()
)

dim_fecha["week_of_year"] = (
    dim_fecha["date"]
    .dt.isocalendar()
    .week.astype("int64")
)

dim_fecha["is_weekend"] = (
    dim_fecha["day_of_week"] >= 6
)

# Registro desconocido
dim_fecha = agregar_unknown(
    dim_fecha,
    "date_key",
    {
        "date": pd.NaT,
        "month_name": "UNKNOWN",
        "day_name": "UNKNOWN",
        "is_weekend": False
    }
)

guardar_parquet(
    dim_fecha,
    "dim_fecha.parquet"
)


# ------------------------------------------------------------
# 4. DIM_IDIOMA
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("4. DIMENSIÓN IDIOMA")
print("=" * 70)

if "language" not in resenas.columns:
    raise ValueError(
        "No existe language en reseñas."
    )

idiomas = (
    resenas["language"]
    .astype("string")
    .str.strip()
    .replace("", pd.NA)
    .dropna()
    .unique()
)

idiomas = sorted(idiomas.tolist())

dim_idioma = pd.DataFrame({
    "language_code": idiomas
})

dim_idioma.insert(
    0,
    "language_key",
    np.arange(1, len(dim_idioma) + 1)
)

dim_idioma = agregar_unknown(
    dim_idioma,
    "language_key",
    {"language_code": "UNKNOWN"}
)

guardar_parquet(
    dim_idioma,
    "dim_idioma.parquet"
)


# ------------------------------------------------------------
# 5. DIM_HARDWARE
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("5. DIMENSIÓN HARDWARE")
print("=" * 70)

columnas_hardware = [
    "hardware.os",
    "hardware.cpu_name",
    "hardware.adapter_description",
    "hardware.system_ram",
    "hardware.vram_size"
]

columnas_existentes = [
    columna
    for columna in columnas_hardware
    if columna in resenas.columns
]

if not columnas_existentes:
    raise ValueError(
        "No se encontraron columnas de hardware."
    )

hardware = resenas[
    columnas_existentes
].copy()

for columna in columnas_existentes:

    hardware[columna] = (
        hardware[columna]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

# Una combinación completamente nula representa
# hardware desconocido, no una combinación independiente.
hardware = hardware.dropna(
    how="all",
    subset=columnas_existentes
)

hardware = hardware.drop_duplicates().reset_index(
    drop=True
)

hardware.insert(
    0,
    "hardware_key",
    np.arange(1, len(hardware) + 1)
)

hardware = agregar_unknown(
    hardware,
    "hardware_key",
    {
        columna: "UNKNOWN"
        for columna in columnas_existentes
    }
)

guardar_parquet(
    hardware,
    "dim_hardware.parquet"
)


# ------------------------------------------------------------
# 6. VALIDACIÓN FINAL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDACIÓN DE DIMENSIONES")
print("=" * 70)

dimensiones = {
    "dim_usuarios": dim_usuarios,
    "dim_juegos": dim_juegos,
    "dim_fecha": dim_fecha,
    "dim_idioma": dim_idioma,
    "dim_hardware": hardware
}

claves_primarias = {
    "dim_usuarios": "user_key",
    "dim_juegos": "game_key",
    "dim_fecha": "date_key",
    "dim_idioma": "language_key",
    "dim_hardware": "hardware_key"
}

for nombre, df in dimensiones.items():

    clave = claves_primarias[nombre]

    nulos = df[clave].isna().sum()
    duplicados = df[clave].duplicated().sum()
    tiene_unknown = (df[clave] == 0).any()

    print(f"\n{nombre}")
    print(f"Registros: {len(df):,}")
    print(f"Clave primaria: {clave}")
    print(f"Claves nulas: {nulos}")
    print(f"Claves duplicadas: {duplicados}")
    print(f"Registro desconocido: {tiene_unknown}")

    if nulos > 0:
        raise ValueError(
            f"Claves nulas en {nombre}."
        )

    if duplicados > 0:
        raise ValueError(
            f"Claves duplicadas en {nombre}."
        )

    if not tiene_unknown:
        raise ValueError(
            f"Falta registro desconocido en {nombre}."
        )

print("\n" + "=" * 70)
print("TODAS LAS DIMENSIONES FUERON VALIDADAS")
print("GOLD - SCRIPT 1 COMPLETADO CORRECTAMENTE")
print("=" * 70)
