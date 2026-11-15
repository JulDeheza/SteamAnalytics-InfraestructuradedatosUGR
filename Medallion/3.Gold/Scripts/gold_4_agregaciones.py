
import pandas as pd
from pathlib import Path

# ============================================================
# GOLD - SCRIPT 4: AGREGACIONES POR JUEGO Y MES
# ============================================================

BASE = Path("/content/Infraestructura-de-ciencia-de-datos/Medallion")
GOLD_DATA = BASE / "3.Gold" / "Data"

ARCHIVOS = {
    "resenas": GOLD_DATA / "fact_resenas.parquet",
    "novedades": GOLD_DATA / "fact_novedades.parquet",
    "fechas": GOLD_DATA / "dim_fecha.parquet"
}

SALIDA = GOLD_DATA / "agg_juego_mes.parquet"

print("=" * 70)
print("GOLD - SCRIPT 4: AGREGACIONES POR JUEGO Y MES")
print("=" * 70)

# ------------------------------------------------------------
# 1. CARGA DE ARCHIVOS
# ------------------------------------------------------------

for nombre, ruta in ARCHIVOS.items():
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

resenas = pd.read_parquet(ARCHIVOS["resenas"])
novedades = pd.read_parquet(ARCHIVOS["novedades"])
fechas = pd.read_parquet(ARCHIVOS["fechas"])

print("\n1. ARCHIVOS CARGADOS")
print(f"Reseñas: {len(resenas):,}")
print(f"Novedades: {len(novedades):,}")
print(f"Fechas: {len(fechas):,}")

# ------------------------------------------------------------
# 2. VALIDACIÓN DE ESTRUCTURAS
# ------------------------------------------------------------

requeridas_resenas = {"recommendationid", "game_key", "date_key"}
requeridas_novedades = {"gid", "game_key", "date_key"}
requeridas_fechas = {"date_key", "year", "month"}

for nombre, df, requeridas in [
    ("resenas", resenas, requeridas_resenas),
    ("novedades", novedades, requeridas_novedades),
    ("fechas", fechas, requeridas_fechas)
]:
    faltantes = requeridas - set(df.columns)
    if faltantes:
        raise ValueError(
            f"Faltan columnas en {nombre}: {sorted(faltantes)}"
        )

if resenas["recommendationid"].isna().any():
    raise ValueError("Hay recommendationid nulos.")

if resenas["recommendationid"].duplicated().any():
    raise ValueError("Hay recommendationid duplicados.")

if novedades["gid"].isna().any():
    raise ValueError("Hay GID nulos.")

if novedades["gid"].duplicated().any():
    raise ValueError("Hay GID duplicados.")

print("\n2. ESTRUCTURAS VALIDADAS")

# ------------------------------------------------------------
# 3. PREPARACIÓN DE DIMENSIÓN FECHA
# ------------------------------------------------------------

fechas = fechas[["date_key", "year", "month"]].copy()

fechas["date_key"] = pd.to_numeric(
    fechas["date_key"], errors="raise"
).astype("int64")

if fechas["date_key"].duplicated().any():
    raise ValueError("dim_fecha contiene date_key duplicados.")

fechas["year"] = pd.to_numeric(
    fechas["year"], errors="coerce"
).fillna(0).astype("int64")

fechas["month"] = pd.to_numeric(
    fechas["month"], errors="coerce"
).fillna(0).astype("int64")

fechas["month_key"] = (
    fechas["year"] * 100 + fechas["month"]
).astype("int64")

# El registro desconocido se representa con período 0.
fechas.loc[fechas["date_key"] == 0, ["year", "month", "month_key"]] = 0

# ------------------------------------------------------------
# 4. FUNCIÓN DE AGREGACIÓN
# ------------------------------------------------------------

def agregar_por_juego_mes(df, identificador, nombre):
    """
    Cuenta registros por juego y mes.
    Cada tabla de hechos se agrega independientemente.
    """

    trabajo = df[
        [identificador, "game_key", "date_key"]
    ].copy()

    trabajo["game_key"] = pd.to_numeric(
        trabajo["game_key"], errors="raise"
    ).astype("int64")

    trabajo["date_key"] = pd.to_numeric(
        trabajo["date_key"], errors="raise"
    ).astype("int64")

    if (trabajo["game_key"] < 0).any():
        raise ValueError(f"{nombre}: game_key negativo.")

    if (trabajo["date_key"] < 0).any():
        raise ValueError(f"{nombre}: date_key negativo.")

    # Incorporar año y mes desde dim_fecha.
    trabajo = trabajo.merge(
        fechas,
        on="date_key",
        how="left",
        validate="many_to_one",
        indicator=True
    )

    sin_fecha = int((trabajo["_merge"] != "both").sum())

    if sin_fecha > 0:
        raise ValueError(
            f"{nombre}: {sin_fecha} registros no encontraron date_key "
            "en dim_fecha."
        )

    trabajo = trabajo.drop(columns=["_merge"])

    resultado = (
        trabajo
        .groupby(
            ["game_key", "year", "month", "month_key"],
            as_index=False,
            dropna=False
        )
        .size()
    )

    resultado = resultado.rename(columns={"size": nombre})

    return resultado


# ------------------------------------------------------------
# 5. AGREGAR RESEÑAS
# ------------------------------------------------------------

print("\n3. AGREGACIÓN DE RESEÑAS")

agg_resenas = agregar_por_juego_mes(
    resenas,
    "recommendationid",
    "cantidad_resenas"
)

print(f"Combinaciones juego-mes: {len(agg_resenas):,}")
print(f"Reseñas contabilizadas: {agg_resenas['cantidad_resenas'].sum():,}")

# ------------------------------------------------------------
# 6. AGREGAR NOVEDADES
# ------------------------------------------------------------

print("\n4. AGREGACIÓN DE NOVEDADES")

agg_novedades = agregar_por_juego_mes(
    novedades,
    "gid",
    "cantidad_novedades"
)

print(f"Combinaciones juego-mes: {len(agg_novedades):,}")
print(
    "Novedades contabilizadas: "
    f"{agg_novedades['cantidad_novedades'].sum():,}"
)

# ------------------------------------------------------------
# 7. CONSOLIDAR AGREGACIONES
# ------------------------------------------------------------

print("\n5. CONSOLIDACIÓN")

agg = agg_resenas.merge(
    agg_novedades,
    on=["game_key", "year", "month", "month_key"],
    how="outer",
    validate="one_to_one"
)

agg["cantidad_resenas"] = (
    agg["cantidad_resenas"].fillna(0).astype("int64")
)

agg["cantidad_novedades"] = (
    agg["cantidad_novedades"].fillna(0).astype("int64")
)

agg["year"] = agg["year"].astype("int64")
agg["month"] = agg["month"].astype("int64")
agg["month_key"] = agg["month_key"].astype("int64")
agg["game_key"] = agg["game_key"].astype("int64")

# Etiqueta legible del período.
agg["periodo"] = agg.apply(
    lambda fila: (
        f"{fila['year']:04d}-{fila['month']:02d}"
        if fila["month_key"] != 0
        else "UNKNOWN"
    ),
    axis=1
)

agg = agg[
    [
        "game_key",
        "year",
        "month",
        "month_key",
        "periodo",
        "cantidad_resenas",
        "cantidad_novedades"
    ]
].sort_values(
    ["game_key", "month_key"]
).reset_index(drop=True)

# ------------------------------------------------------------
# 8. VALIDACIONES FINALES
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDACIÓN FINAL - AGG_JUEGO_MES")
print("=" * 70)

if agg.duplicated(
    subset=["game_key", "year", "month"]
).any():
    raise ValueError("Hay combinaciones juego-mes duplicadas.")

if agg.isna().any().any():
    raise ValueError("La agregación contiene valores nulos.")

if (agg["game_key"] < 0).any():
    raise ValueError("Se detectaron game_key negativos.")

if (agg["cantidad_resenas"] < 0).any():
    raise ValueError("Hay cantidades de reseñas negativas.")

if (agg["cantidad_novedades"] < 0).any():
    raise ValueError("Hay cantidades de novedades negativas.")

total_resenas = int(agg["cantidad_resenas"].sum())
total_novedades = int(agg["cantidad_novedades"].sum())

if total_resenas != len(resenas):
    raise ValueError(
        f"Conteo de reseñas inconsistente: {total_resenas} "
        f"contra {len(resenas)}."
    )

if total_novedades != len(novedades):
    raise ValueError(
        f"Conteo de novedades inconsistente: {total_novedades} "
        f"contra {len(novedades)}."
    )

print("OK: Combinaciones juego-mes sin duplicados.")
print("OK: Sin valores nulos.")
print("OK: Claves sustitutas válidas.")
print("OK: Total de reseñas conservado.")
print("OK: Total de novedades conservado.")

# ------------------------------------------------------------
# 9. GUARDAR RESULTADO
# ------------------------------------------------------------

agg.to_parquet(SALIDA, index=False)

print("\n" + "=" * 70)
print("RESUMEN AGG_JUEGO_MES")
print("=" * 70)

print(f"Filas: {len(agg):,}")
print(f"Columnas: {len(agg.columns)}")
print(f"Reseñas contabilizadas: {total_resenas:,}")
print(f"Novedades contabilizadas: {total_novedades:,}")
print(f"Juegos distintos: {agg['game_key'].nunique():,}")
print(f"Períodos distintos: {agg['month_key'].nunique():,}")
print(f"Archivo generado: {SALIDA}")

print("\nGOLD - SCRIPT 4 COMPLETADO CORRECTAMENTE")
