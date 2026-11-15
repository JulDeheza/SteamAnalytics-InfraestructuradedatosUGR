
import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURACIÓN DE RUTAS
# ============================================================

BASE_DIR = Path(
    "/content/Infraestructura-de-ciencia-de-datos/Medallion"
)

SILVER_DATA_DIR = BASE_DIR / "2.Silver" / "Data"
RECORTES_DIR = SILVER_DATA_DIR / "recortes"

ARCHIVO_ENTRADA = SILVER_DATA_DIR / "novedades_juegos.parquet"

RECORTES_DIR.mkdir(parents=True, exist_ok=True)

ANIOS_OBJETIVO = range(2020, 2026)

print("=" * 65)
print("CAPA SILVER - SCRIPT 4: RECORTES ANUALES")
print("=" * 65)

# ============================================================
# 1. CARGA DE NOVEDADES
# ============================================================

print("\\n1. Cargando novedades enriquecidas...")

if not ARCHIVO_ENTRADA.exists():
    raise FileNotFoundError(
        f"No se encontró: {ARCHIVO_ENTRADA}. "
        "Ejecutá primero el Script 3."
    )

df = pd.read_parquet(ARCHIVO_ENTRADA)

if df.empty:
    raise ValueError("El archivo de novedades está vacío.")

filas_originales = len(df)

print(f"Novedades disponibles: {filas_originales:,}")

# ============================================================
# 2. VALIDACIÓN DE COLUMNAS
# ============================================================

print("\\n2. Validando estructura...")

columnas_obligatorias = ["gid", "date_parsed", "year"]

for columna in columnas_obligatorias:
    if columna not in df.columns:
        raise ValueError(
            f"Falta la columna obligatoria: {columna}"
        )

if df["gid"].isna().any():
    raise ValueError("Se encontraron GID nulos.")

if df["gid"].duplicated().any():
    raise ValueError("Se encontraron GID duplicados.")

# ============================================================
# 3. NORMALIZACIÓN DE AÑO
# ============================================================

print("\\n3. Normalizando años...")

df["date_parsed"] = pd.to_datetime(
    df["date_parsed"],
    errors="coerce",
    utc=True
)

df["year"] = df["date_parsed"].dt.year.astype("Int64")

fechas_invalidas = df["year"].isna().sum()

print(f"Fechas sin año válido: {fechas_invalidas:,}")

# ============================================================
# 4. GENERACIÓN DE RECORTES
# ============================================================

print("\\n4. Generando archivos anuales...")

resultados = []

for anio in ANIOS_OBJETIVO:

    df_anual = df.loc[
        df["year"] == anio
    ].copy()

    ruta_salida = RECORTES_DIR / f"novedades_{anio}.parquet"

    df_anual.to_parquet(
        ruta_salida,
        engine="pyarrow",
        index=False
    )

    # Verificación individual
    df_verificacion = pd.read_parquet(ruta_salida)

    if len(df_verificacion) != len(df_anual):
        raise ValueError(
            f"Error de exportación en el año {anio}."
        )

    resultados.append({
        "anio": anio,
        "registros": len(df_anual),
        "archivo": ruta_salida.name
    })

    print(
        f"{anio}: {len(df_anual):,} registros | "
        f"{ruta_salida.name}"
    )

# ============================================================
# 5. VALIDACIÓN DE INTEGRIDAD
# ============================================================

print("\\n5. Validando recortes...")

total_recortes = sum(
    resultado["registros"]
    for resultado in resultados
)

# Registros que pertenecen al período solicitado
total_periodo = df["year"].between(
    2020, 2025
).sum()

if total_recortes != total_periodo:
    raise ValueError(
        "La suma de recortes no coincide con el total "
        "de novedades del período 2020-2025."
    )

# Comprobar que no haya GID repetidos entre recortes
gids_recortes = []

for anio in ANIOS_OBJETIVO:

    ruta = RECORTES_DIR / f"novedades_{anio}.parquet"

    df_anual = pd.read_parquet(ruta)

    gids_recortes.extend(df_anual["gid"].astype(str).tolist())

if len(gids_recortes) != len(set(gids_recortes)):
    raise ValueError(
        "Se encontraron GID repetidos entre los recortes."
    )

print(f"Total de registros del período: {total_periodo:,}")
print(f"Total exportado: {total_recortes:,}")
print("Integridad de los recortes: OK")

# ============================================================
# 6. INFORME FINAL
# ============================================================

print("\\n" + "=" * 65)
print("RESULTADO - SCRIPT 4")
print("=" * 65)

print(f"Novedades originales: {filas_originales:,}")
print(f"Novedades 2020-2025: {total_periodo:,}")
print(f"Total de recortes: {len(resultados)}")

for resultado in resultados:
    print(
        f"{resultado['anio']}: "
        f"{resultado['registros']:,} registros"
    )

print("\\nDirectorio de salida:")
print(RECORTES_DIR)

print("\\nSCRIPT 4 FINALIZADO CORRECTAMENTE.")
