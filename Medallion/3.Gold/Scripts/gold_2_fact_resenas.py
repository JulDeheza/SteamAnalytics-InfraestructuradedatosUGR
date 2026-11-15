
# ============================================================
# GOLD - SCRIPT 2: CONSTRUCCIÓN FACT RESEÑAS
# Archivo: gold_2_fact_resenas.py
# Granularidad: una fila por recommendationid
# ============================================================

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/content/Infraestructura-de-ciencia-de-datos")

SILVER_DATA = ROOT / "Medallion" / "2.Silver" / "Data"
GOLD_DATA = ROOT / "Medallion" / "3.Gold" / "Data"
GOLD_SCRIPTS = ROOT / "Medallion" / "3.Gold" / "Scripts"

GOLD_DATA.mkdir(parents=True, exist_ok=True)
GOLD_SCRIPTS.mkdir(parents=True, exist_ok=True)

ARCHIVO_SALIDA = GOLD_DATA / "fact_resenas.parquet"


def cargar_parquet(ruta):
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    df = pd.read_parquet(ruta)
    print(f"Cargado: {ruta.name} | Filas: {len(df):,}")
    return df


def normalizar_texto(serie):
    """
    Normaliza texto para realizar uniones.
    Los nulos se mantienen como un valor especial para
    permitir coincidencias de hardware parcialmente informado.
    """
    resultado = serie.astype("string").str.strip()
    resultado = resultado.replace("", pd.NA)
    return resultado.fillna("__NULL__")


def obtener_fecha_reseña(df):
    """
    Prioriza timestamp_created_parsed.
    Si no existe o está vacío, utiliza timestamp_created
    interpretándolo como Unix timestamp en segundos.
    """
    if "timestamp_created_parsed" in df.columns:
        fecha = pd.to_datetime(
            df["timestamp_created_parsed"],
            errors="coerce",
            utc=True
        )
    else:
        fecha = pd.Series(
            pd.NaT,
            index=df.index,
            dtype="datetime64[ns, UTC]"
        )

    if "timestamp_created" in df.columns:
        fecha_original = pd.to_datetime(
            pd.to_numeric(df["timestamp_created"], errors="coerce"),
            unit="s",
            errors="coerce",
            utc=True
        )

        fecha = fecha.fillna(fecha_original)

    return fecha.dt.normalize()


def validar_columnas(df, requeridas, nombre):
    faltantes = [col for col in requeridas if col not in df.columns]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {nombre}: {faltantes}"
        )


print("=" * 70)
print("GOLD - SCRIPT 2: CONSTRUCCIÓN FACT RESEÑAS")
print("=" * 70)


# ------------------------------------------------------------
# 1. CARGA DE ARCHIVOS
# ------------------------------------------------------------

print("\n1. CARGANDO ARCHIVOS")

resenas = cargar_parquet(SILVER_DATA / "resenas.parquet")

dim_usuarios = cargar_parquet(GOLD_DATA / "dim_usuarios.parquet")
dim_juegos = cargar_parquet(GOLD_DATA / "dim_juegos.parquet")
dim_fecha = cargar_parquet(GOLD_DATA / "dim_fecha.parquet")
dim_idioma = cargar_parquet(GOLD_DATA / "dim_idioma.parquet")
dim_hardware = cargar_parquet(GOLD_DATA / "dim_hardware.parquet")


# ------------------------------------------------------------
# 2. VALIDACIÓN DE COLUMNAS NECESARIAS
# ------------------------------------------------------------

print("\n2. VALIDANDO ESTRUCTURAS")

validar_columnas(
    resenas,
    ["recommendationid", "steamid", "appid"],
    "resenas"
)

validar_columnas(
    dim_usuarios,
    ["user_key", "steamid"],
    "dim_usuarios"
)

validar_columnas(
    dim_juegos,
    ["game_key", "appid"],
    "dim_juegos"
)

validar_columnas(
    dim_fecha,
    ["date_key", "date"],
    "dim_fecha"
)

validar_columnas(
    dim_idioma,
    ["language_key", "language_code"],
    "dim_idioma"
)

columnas_hardware = [
    "hardware.os",
    "hardware.cpu_name",
    "hardware.adapter_description",
    "hardware.system_ram",
    "hardware.vram_size"
]

validar_columnas(
    dim_hardware,
    ["hardware_key"] + columnas_hardware,
    "dim_hardware"
)

if resenas["recommendationid"].isna().any():
    raise ValueError("Hay recommendationid nulos en Silver.")

if resenas["recommendationid"].duplicated().any():
    raise ValueError("Hay recommendationid duplicados en Silver.")

print("Estructuras verificadas.")
print("Reseñas de origen:", f"{len(resenas):,}")


# ------------------------------------------------------------
# 3. PREPARACIÓN DE CLAVES NATURALES
# ------------------------------------------------------------

print("\n3. PREPARANDO CLAVES NATURALES")

resenas["steamid"] = resenas["steamid"].astype("string").str.strip()
dim_usuarios["steamid"] = (
    dim_usuarios["steamid"].astype("string").str.strip()
)

resenas["appid"] = pd.to_numeric(
    resenas["appid"], errors="coerce"
).astype("Int64")

dim_juegos["appid"] = pd.to_numeric(
    dim_juegos["appid"], errors="coerce"
).astype("Int64")

# La fecha de publicación de la reseña determina date_key.
resenas["_fecha_reseña"] = obtener_fecha_reseña(resenas)

dim_fecha["_fecha_dimension"] = pd.to_datetime(
    dim_fecha["date"],
    errors="coerce",
    utc=True
).dt.normalize()

# Se calcula YYYYMMDD para asociar la fecha con la dimensión.
resenas["date_key"] = (
    resenas["_fecha_reseña"].dt.strftime("%Y%m%d")
)

dim_fecha["_date_key_join"] = (
    dim_fecha["_fecha_dimension"].dt.strftime("%Y%m%d")
)

resenas["date_key"] = pd.to_numeric(
    resenas["date_key"], errors="coerce"
).astype("Int64")

dim_fecha["_date_key_join"] = pd.to_numeric(
    dim_fecha["_date_key_join"], errors="coerce"
).astype("Int64")

# Idioma.
resenas["_language_join"] = normalizar_texto(resenas["language"])
dim_idioma["_language_join"] = normalizar_texto(
    dim_idioma["language_code"]
)

# Hardware.
for columna in columnas_hardware:
    resenas[f"_{columna}_join"] = normalizar_texto(
        resenas[columna]
    )
    dim_hardware[f"_{columna}_join"] = normalizar_texto(
        dim_hardware[columna]
    )

print("Claves naturales preparadas.")


# ------------------------------------------------------------
# 4. ASOCIACIÓN CON DIM_USUARIOS
# ------------------------------------------------------------

print("\n4. ASOCIANDO USUARIOS")

mapa_usuarios = dim_usuarios[
    ["steamid", "user_key"]
].copy()

if mapa_usuarios["steamid"].duplicated().any():
    raise ValueError("steamid duplicados en dim_usuarios.")

fact = resenas.merge(
    mapa_usuarios,
    on="steamid",
    how="left",
    validate="many_to_one"
)

usuarios_sin_match = fact["user_key"].isna().sum()
fact["user_key"] = fact["user_key"].fillna(0).astype("int64")

print("Reseñas sin usuario asociado:", f"{usuarios_sin_match:,}")
print("Asignadas a user_key = 0:", f"{usuarios_sin_match:,}")


# ------------------------------------------------------------
# 5. ASOCIACIÓN CON DIM_JUEGOS
# ------------------------------------------------------------

print("\n5. ASOCIANDO JUEGOS")

mapa_juegos = dim_juegos[
    ["appid", "game_key"]
].copy()

if mapa_juegos["appid"].dropna().duplicated().any():
    raise ValueError("appid duplicados en dim_juegos.")

fact = fact.merge(
    mapa_juegos,
    on="appid",
    how="left",
    validate="many_to_one"
)

juegos_sin_match = fact["game_key"].isna().sum()
fact["game_key"] = fact["game_key"].fillna(0).astype("int64")

print("Reseñas sin juego asociado:", f"{juegos_sin_match:,}")
print("Asignadas a game_key = 0:", f"{juegos_sin_match:,}")



# ------------------------------------------------------------
# 6. ASOCIACIÓN CON DIM_FECHA
# ------------------------------------------------------------

print("\n6. ASOCIANDO FECHAS")

# ------------------------------------------------------------
# 6.1. OBTENER FECHAS DE LAS RESEÑAS
# ------------------------------------------------------------

resenas["_fecha_reseña"] = obtener_fecha_reseña(resenas)

resenas["date_key"] = pd.to_numeric(
    resenas["_fecha_reseña"].dt.strftime("%Y%m%d"),
    errors="coerce"
).astype("Int64")

# ------------------------------------------------------------
# 6.2. NORMALIZAR DIM_FECHA
# ------------------------------------------------------------

dim_fecha["_fecha_dimension"] = pd.to_datetime(
    dim_fecha["date"],
    errors="coerce",
    utc=True
).dt.normalize()

dim_fecha["_date_key_join"] = pd.to_numeric(
    dim_fecha["_fecha_dimension"].dt.strftime("%Y%m%d"),
    errors="coerce"
).astype("Int64")

# Claves de fechas que ya existen en la dimensión.
fechas_existentes = set(
    dim_fecha.loc[
        dim_fecha["date_key"] != 0,
        "date_key"
    ].dropna().astype("int64")
)

# Claves de fechas que aparecen en las reseñas.
fechas_requeridas = set(
    resenas["date_key"].dropna().astype("int64")
)

# Identificar fechas faltantes.
fechas_faltantes = sorted(
    fechas_requeridas - fechas_existentes
)

print("Fechas existentes:", f"{len(fechas_existentes):,}")
print("Fechas requeridas:", f"{len(fechas_requeridas):,}")
print("Fechas faltantes:", f"{len(fechas_faltantes):,}")

# ------------------------------------------------------------
# 6.3. INCORPORAR FECHAS FALTANTES
# ------------------------------------------------------------

if fechas_faltantes:

    fechas_nuevas = pd.to_datetime(
        pd.Series(fechas_faltantes, dtype="int64").astype(str),
        format="%Y%m%d",
        errors="coerce",
        utc=True
    )

    nuevas_filas = pd.DataFrame({
        "date": fechas_nuevas,
        "date_key": fechas_faltantes,
        "year": fechas_nuevas.dt.year,
        "quarter": fechas_nuevas.dt.quarter,
        "month": fechas_nuevas.dt.month,
        "month_name": fechas_nuevas.dt.month_name(),
        "day": fechas_nuevas.dt.day,
        "day_of_week": fechas_nuevas.dt.dayofweek + 1,
        "day_name": fechas_nuevas.dt.day_name(),
        "week_of_year": (
            fechas_nuevas.dt.isocalendar().week.astype("Int64")
        ),
        "is_weekend": fechas_nuevas.dt.dayofweek >= 5
    })

    # Mantener exactamente las columnas de dim_fecha.
    nuevas_filas = nuevas_filas.reindex(
        columns=[
            col for col in dim_fecha.columns
            if col in nuevas_filas.columns
        ]
    )

    # Agregar fechas nuevas sin duplicar registros.
    dim_fecha = pd.concat(
        [
            dim_fecha.drop(
                columns=["_fecha_dimension", "_date_key_join"],
                errors="ignore"
            ),
            nuevas_filas
        ],
        ignore_index=True
    )

    # Guardar dimensión actualizada.
    dim_fecha.to_parquet(
        GOLD_DATA / "dim_fecha.parquet",
        index=False
    )

    print(
        "Dimensión actualizada con",
        f"{len(fechas_faltantes):,}",
        "fechas nuevas."
    )

else:
    dim_fecha = dim_fecha.drop(
        columns=["_fecha_dimension", "_date_key_join"],
        errors="ignore"
    )

    print("No fue necesario incorporar fechas nuevas.")

# ------------------------------------------------------------
# 6.4. VALIDAR DIM_FECHA ACTUALIZADA
# ------------------------------------------------------------

if dim_fecha["date_key"].duplicated().any():
    raise ValueError(
        "Hay claves duplicadas en dim_fecha después de actualizarla."
    )

if not (dim_fecha["date_key"] == 0).any():
    raise ValueError(
        "La dimensión fecha perdió su registro desconocido."
    )

# ------------------------------------------------------------
# 6.5. ASIGNAR CLAVES A FACT_RESEÑAS
# ------------------------------------------------------------

claves_fecha_validas = set(
    dim_fecha["date_key"].astype("int64")
)

fechas_validas = resenas["date_key"].isin(
    claves_fecha_validas
)

fecha_sin_match = (~fechas_validas).sum()

# Los registros sin fecha válida se asignan al registro desconocido.
fact["date_key"] = (
    resenas["date_key"]
    .where(fechas_validas, 0)
    .fillna(0)
    .astype("int64")
)

print("Reseñas sin fecha asociada:", f"{fecha_sin_match:,}")
print(
    "Reseñas asociadas a fechas válidas:",
    f"{len(fact) - fecha_sin_match:,}"
)
print(
    "Reseñas asignadas a date_key = 0:",
    f"{(fact['date_key'] == 0).sum():,}"
)

print(
    "Total de registros en dim_fecha:",
    f"{len(dim_fecha):,}"
)

# ------------------------------------------------------------
# 7. ASOCIACIÓN CON DIM_IDIOMA
# ------------------------------------------------------------

print("\n7. ASOCIANDO IDIOMAS")

mapa_idiomas = dim_idioma[
    ["_language_join", "language_key"]
].copy()

if mapa_idiomas["_language_join"].duplicated().any():
    raise ValueError("Idiomas duplicados en dim_idioma.")

fact = fact.merge(
    mapa_idiomas,
    on="_language_join",
    how="left",
    validate="many_to_one"
)

idiomas_sin_match = fact["language_key"].isna().sum()
fact["language_key"] = (
    fact["language_key"].fillna(0).astype("int64")
)

print("Reseñas sin idioma asociado:", f"{idiomas_sin_match:,}")
print("Asignadas a language_key = 0:", f"{idiomas_sin_match:,}")


# ------------------------------------------------------------
# 8. ASOCIACIÓN CON DIM_HARDWARE
# ------------------------------------------------------------

print("\n8. ASOCIANDO HARDWARE")

columnas_union_hardware = [
    f"_{columna}_join" for columna in columnas_hardware
]

mapa_hardware = dim_hardware[
    columnas_union_hardware + ["hardware_key"]
].copy()

if mapa_hardware.duplicated(
    subset=columnas_union_hardware
).any():
    raise ValueError(
        "Hay combinaciones de hardware duplicadas en dim_hardware."
    )

fact = fact.merge(
    mapa_hardware,
    on=columnas_union_hardware,
    how="left",
    validate="many_to_one"
)

hardware_sin_match = fact["hardware_key"].isna().sum()
fact["hardware_key"] = (
    fact["hardware_key"].fillna(0).astype("int64")
)

print("Reseñas sin hardware asociado:", f"{hardware_sin_match:,}")
print("Asignadas a hardware_key = 0:", f"{hardware_sin_match:,}")


# ------------------------------------------------------------
# 9. CONSTRUCCIÓN DE FACT_RESEÑAS
# ------------------------------------------------------------

print("\n9. CONSTRUYENDO FACT_RESEÑAS")

# Se conservan los identificadores naturales para trazabilidad,
# las claves sustitutas y los atributos propios de cada reseña.
columnas_fact = [
    "recommendationid",
    "user_key",
    "game_key",
    "date_key",
    "language_key",
    "hardware_key",
    "steamid",
    "appid",
    "review",
    "timestamp_created",
    "timestamp_updated",
    "timestamp_created_parsed",
    "timestamp_updated_parsed",
    "voted_up",
    "votes_up",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",
    "steam_purchase",
    "received_for_free",
    "written_during_early_access",
    "primarily_steam_deck",
    "refunded",
    "author.num_reviews",
    "author.playtime_forever",
    "author.playtime_last_two_weeks",
    "author.playtime_at_review",
    "author.last_played",
    "author.last_played_parsed",
    "author.deck_playtime_at_review",
    "developer_response",
    "timestamp_dev_responded",
    "timestamp_dev_responded_parsed"
]

columnas_fact = [
    columna for columna in columnas_fact
    if columna in fact.columns
]

fact_resenas = fact[columnas_fact].copy()

# Tipos enteros para claves sustitutas.
claves = [
    "user_key",
    "game_key",
    "date_key",
    "language_key",
    "hardware_key"
]

for clave in claves:
    fact_resenas[clave] = (
        pd.to_numeric(fact_resenas[clave], errors="coerce")
        .fillna(0)
        .astype("int64")
    )

# Control de granularidad.
if fact_resenas["recommendationid"].duplicated().any():
    raise ValueError(
        "La tabla fact_resenas contiene recommendationid duplicados."
    )

if len(fact_resenas) != len(resenas):
    raise ValueError(
        "La cantidad de filas cambió durante las asociaciones."
    )

fact_resenas.to_parquet(
    ARCHIVO_SALIDA,
    index=False
)

print("Archivo guardado:", ARCHIVO_SALIDA.name)
print("Filas:", f"{len(fact_resenas):,}")
print("Columnas:", len(fact_resenas.columns))


# ------------------------------------------------------------
# 10. VALIDACIÓN FINAL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDACIÓN FINAL - FACT_RESEÑAS")
print("=" * 70)

controles = {
    "Misma cantidad de filas que Silver":
        len(fact_resenas) == len(resenas),

    "recommendationid sin nulos":
        fact_resenas["recommendationid"].notna().all(),

    "recommendationid sin duplicados":
        not fact_resenas["recommendationid"].duplicated().any(),

    "user_key sin nulos":
        fact_resenas["user_key"].notna().all(),

    "game_key sin nulos":
        fact_resenas["game_key"].notna().all(),

    "date_key sin nulos":
        fact_resenas["date_key"].notna().all(),

    "language_key sin nulos":
        fact_resenas["language_key"].notna().all(),

    "hardware_key sin nulos":
        fact_resenas["hardware_key"].notna().all(),

    "Claves sustitutas no negativas":
        all((fact_resenas[c] >= 0).all() for c in claves)
}

for nombre, resultado in controles.items():
    estado = "OK" if resultado else "ERROR"
    print(f"{estado}: {nombre}")

errores = [
    nombre for nombre, resultado in controles.items()
    if not resultado
]

print("\nRESUMEN DE ASOCIACIONES")
print("Total de reseñas:", f"{len(fact_resenas):,}")
print("Usuarios sin asociación:", f"{usuarios_sin_match:,}")
print("Juegos sin asociación:", f"{juegos_sin_match:,}")
print("Fechas sin asociación:", f"{fecha_sin_match:,}")
print("Idiomas sin asociación:", f"{idiomas_sin_match:,}")
print("Hardware sin asociación:", f"{hardware_sin_match:,}")

if errores:
    raise ValueError(
        "FACT_RESEÑAS NO SUPERÓ LA VALIDACIÓN: " + ", ".join(errores)
    )

print("\n" + "=" * 70)
print("GOLD - SCRIPT 2 COMPLETADO CORRECTAMENTE")
print("=" * 70)
