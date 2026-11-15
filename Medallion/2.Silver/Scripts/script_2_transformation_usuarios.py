
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

ARCHIVO_ENTRADA = BRONZE_DATA_DIR / "usuarios.json"
ARCHIVO_SALIDA = SILVER_DATA_DIR / "usuarios.parquet"

SILVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CAPA SILVER - SCRIPT 2: TRANSFORMACIÓN DE USUARIOS")
print("=" * 65)

# ============================================================
# 1. CARGA DE DATOS BRONZE
# ============================================================

print("\\n1. Cargando usuarios desde Bronze...")

if not ARCHIVO_ENTRADA.exists():
    raise FileNotFoundError(
        f"No se encontró el archivo: {ARCHIVO_ENTRADA}"
    )

with open(ARCHIVO_ENTRADA, "r", encoding="utf-8") as archivo:
    data = json.load(archivo)

if isinstance(data, dict) and "users" in data:
    registros = data["users"]
else:
    raise ValueError(
        "La estructura de usuarios.json no contiene la clave 'users'."
    )

if not isinstance(registros, list):
    raise TypeError("La clave 'users' no contiene una lista.")

df = pd.DataFrame(registros)

if df.empty:
    raise ValueError("El archivo de usuarios no contiene registros.")

filas_originales = len(df)

print(f"Usuarios cargados: {filas_originales:,}")

# ============================================================
# 2. VALIDACIÓN DE ESTRUCTURA
# ============================================================

print("\\n2. Validando estructura...")

if "steamid" not in df.columns:
    raise ValueError("No existe la columna obligatoria 'steamid'.")

if df["steamid"].isna().any():
    raise ValueError(
        "Se encontraron SteamID nulos. "
        "Se detiene el proceso para evitar perder registros."
    )

# Normalizar identificadores como texto
df["steamid"] = df["steamid"].astype("string").str.strip()

if (df["steamid"] == "").any():
    raise ValueError("Se encontraron SteamID vacíos.")

if df["steamid"].duplicated().any():
    duplicados = df.loc[
        df["steamid"].duplicated(keep=False),
        "steamid"
    ]

    raise ValueError(
        f"Se encontraron {len(duplicados):,} registros "
        "con SteamID duplicados."
    )

# ============================================================
# 3. TRANSFORMACIÓN DE FECHA DE CREACIÓN
# ============================================================

print("\\n3. Transformando fecha de creación...")

if "timecreated" in df.columns:

    # Conversión numérica sin eliminar valores faltantes
    df["timecreated_numeric"] = pd.to_numeric(
        df["timecreated"],
        errors="coerce"
    )

    # Validar rango razonable de timestamps Unix
    mascara_valida = (
        df["timecreated_numeric"].notna()
        & (df["timecreated_numeric"] > 0)
        & (df["timecreated_numeric"] < 3_000_000_000)
    )

    # Crear fecha interpretada en UTC
    df["timecreated_parsed"] = pd.to_datetime(
        df["timecreated_numeric"].where(mascara_valida),
        unit="s",
        errors="coerce",
        utc=True
    )

    fechas_validas = df["timecreated_parsed"].notna().sum()
    fechas_nulas = df["timecreated_parsed"].isna().sum()

    print(f"Fechas válidas: {fechas_validas:,}")
    print(f"Fechas nulas o inválidas: {fechas_nulas:,}")

else:
    print("No existe timecreated. No se generan columnas de fecha.")

# ============================================================
# 4. VALIDACIÓN DE INTEGRIDAD
# ============================================================

print("\\n4. Ejecutando controles de integridad...")

if len(df) != filas_originales:
    raise ValueError(
        "La cantidad de filas cambió durante la transformación."
    )

if df["steamid"].isna().any():
    raise ValueError("Se detectaron SteamID nulos.")

if df["steamid"].duplicated().any():
    raise ValueError("Se detectaron SteamID duplicados.")

print("Cantidad de filas: OK")
print("SteamID nulos: 0")
print("SteamID duplicados: 0")

# ============================================================
# 5. ORDENAMIENTO
# ============================================================

df = df.sort_values(
    by="steamid",
    ascending=True
).reset_index(drop=True)

# ============================================================
# 6. EXPORTACIÓN A PARQUET
# ============================================================

print("\\n5. Exportando archivo Parquet...")

df.to_parquet(
    ARCHIVO_SALIDA,
    engine="pyarrow",
    index=False
)

# ============================================================
# 7. VALIDACIÓN DEL ARCHIVO EXPORTADO
# ============================================================

df_verificacion = pd.read_parquet(ARCHIVO_SALIDA)

if len(df_verificacion) != filas_originales:
    raise ValueError(
        "La cantidad de filas del Parquet no coincide con Bronze."
    )

if df_verificacion["steamid"].duplicated().any():
    raise ValueError(
        "El Parquet contiene SteamID duplicados."
    )

tamano_mb = ARCHIVO_SALIDA.stat().st_size / (1024 ** 2)

# ============================================================
# 8. INFORME FINAL
# ============================================================

print("\\n" + "=" * 65)
print("RESULTADO - SCRIPT 2")
print("=" * 65)

print(f"Filas originales: {filas_originales:,}")
print(f"Filas Silver: {len(df_verificacion):,}")
print(f"Columnas: {len(df_verificacion.columns)}")
print(f"SteamID únicos: {df_verificacion['steamid'].nunique():,}")
print(f"Tamaño: {tamano_mb:.2f} MB")

print("\\nColumnas generadas:")

for columna in df_verificacion.columns:
    print(f"- {columna}: {df_verificacion[columna].dtype}")

print("\\nArchivo generado:")
print(ARCHIVO_SALIDA)

print("\\nSCRIPT 2 FINALIZADO CORRECTAMENTE.")
