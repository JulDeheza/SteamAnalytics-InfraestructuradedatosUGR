
"""
CAPA SILVER - SCRIPT 6: CONSOLIDACIÓN
Integra reseñas con juegos y usuarios.
Mantiene novedades como conjunto independiente.
"""

import json
import pandas as pd
from pathlib import Path

# ============================================================
# 1. CONFIGURACIÓN DE RUTAS
# ============================================================

ROOT = Path("/content/Infraestructura-de-ciencia-de-datos")

BRONZE_DATA = ROOT / "Medallion" / "1.Bronze" / "Data"
SILVER_DATA = ROOT / "Medallion" / "2.Silver" / "Data"
SILVER_SCRIPTS = ROOT / "Medallion" / "2.Silver" / "Scripts"

SILVER_DATA.mkdir(parents=True, exist_ok=True)
SILVER_SCRIPTS.mkdir(parents=True, exist_ok=True)

ARCHIVOS = {
    "juegos": SILVER_DATA / "juegos.parquet",
    "usuarios": SILVER_DATA / "usuarios.parquet",
    "resenas": SILVER_DATA / "resenas.parquet",
    "novedades": SILVER_DATA / "novedades_juegos.parquet"
}

SALIDA_RESENAS = SILVER_DATA / "resenas_consolidadas.parquet"
SALIDA_NOVEDADES = SILVER_DATA / "novedades_consolidadas.parquet"


# ============================================================
# 2. CARGA DE DATOS
# ============================================================

print("=" * 65)
print("CAPA SILVER - SCRIPT 6: CONSOLIDACIÓN")
print("=" * 65)

print("\n1. Verificando archivos de entrada...")

for nombre, ruta in ARCHIVOS.items():
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo {nombre}: {ruta}"
        )

print("Todos los archivos necesarios están disponibles.")

print("\n2. Cargando tablas Silver...")

juegos = pd.read_parquet(ARCHIVOS["juegos"])
usuarios = pd.read_parquet(ARCHIVOS["usuarios"])
resenas = pd.read_parquet(ARCHIVOS["resenas"])
novedades = pd.read_parquet(ARCHIVOS["novedades"])

print(f"Juegos: {len(juegos):,}")
print(f"Usuarios: {len(usuarios):,}")
print(f"Reseñas: {len(resenas):,}")
print(f"Novedades: {len(novedades):,}")


# ============================================================
# 3. VALIDACIÓN DE ESTRUCTURA
# ============================================================

print("\n3. Validando columnas y claves...")

requeridas = {
    "juegos": ["appid"],
    "usuarios": ["steamid"],
    "resenas": ["recommendationid", "appid", "steamid"],
    "novedades": ["gid"]
}

tablas = {
    "juegos": juegos,
    "usuarios": usuarios,
    "resenas": resenas,
    "novedades": novedades
}

for nombre, columnas in requeridas.items():
    faltantes = [
        columna for columna in columnas
        if columna not in tablas[nombre].columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {nombre}: {faltantes}"
        )

# Normalización de identificadores
juegos["appid"] = pd.to_numeric(
    juegos["appid"], errors="coerce"
).astype("Int64")

resenas["appid"] = pd.to_numeric(
    resenas["appid"], errors="coerce"
).astype("Int64")

usuarios["steamid"] = usuarios["steamid"].astype("string").str.strip()
resenas["steamid"] = resenas["steamid"].astype("string").str.strip()

juegos["appid"] = juegos["appid"].astype("Int64")

# Validación de claves principales
if juegos["appid"].isna().any():
    raise ValueError("Hay APPID nulos en juegos.")

if juegos["appid"].duplicated().any():
    raise ValueError("Hay APPID duplicados en juegos.")

if usuarios["steamid"].isna().any():
    raise ValueError("Hay SteamID nulos en usuarios.")

if usuarios["steamid"].duplicated().any():
    raise ValueError("Hay SteamID duplicados en usuarios.")

if resenas["recommendationid"].isna().any():
    raise ValueError("Hay RecommendationID nulos en reseñas.")

if resenas["recommendationid"].duplicated().any():
    raise ValueError("Hay RecommendationID duplicados en reseñas.")

if novedades["gid"].isna().any():
    raise ValueError("Hay GID nulos en novedades.")

if novedades["gid"].duplicated().any():
    raise ValueError("Hay GID duplicados en novedades.")

print("Claves principales validadas correctamente.")


# ============================================================
# 4. CONSOLIDACIÓN DE RESEÑAS + JUEGOS
# ============================================================

print("\n4. Relacionando reseñas con juegos...")

filas_resenas_originales = len(resenas)

resenas_consolidadas = resenas.merge(
    juegos,
    on="appid",
    how="left",
    validate="many_to_one",
    indicator="_game_merge",
    suffixes=("", "_game")
)

resenas_consolidadas["game_match_status"] = (
    resenas_consolidadas["_game_merge"]
    .map({
        "both": "MATCH",
        "left_only": "NO_MATCH"
    })
)

resenas_consolidadas.drop(
    columns=["_game_merge"],
    inplace=True
)

coincidencias_juegos = (
    resenas_consolidadas["game_match_status"] == "MATCH"
).sum()

sin_juego = (
    resenas_consolidadas["game_match_status"] == "NO_MATCH"
).sum()

print(f"Reseñas asociadas a juegos: {coincidencias_juegos:,}")
print(f"Reseñas sin juego asociado: {sin_juego:,}")


# ============================================================
# 5. CONSOLIDACIÓN CON USUARIOS
# ============================================================

print("\n5. Relacionando reseñas con usuarios...")

resenas_consolidadas = resenas_consolidadas.merge(
    usuarios,
    on="steamid",
    how="left",
    validate="many_to_one",
    indicator="_user_merge",
    suffixes=("", "_user")
)

resenas_consolidadas["user_match_status"] = (
    resenas_consolidadas["_user_merge"]
    .map({
        "both": "MATCH",
        "left_only": "NO_MATCH"
    })
)

resenas_consolidadas.drop(
    columns=["_user_merge"],
    inplace=True
)

coincidencias_usuarios = (
    resenas_consolidadas["user_match_status"] == "MATCH"
).sum()

sin_usuario = (
    resenas_consolidadas["user_match_status"] == "NO_MATCH"
).sum()

print(f"Reseñas asociadas a usuarios: {coincidencias_usuarios:,}")
print(f"Reseñas sin usuario asociado: {sin_usuario:,}")


# ============================================================
# 6. VALIDACIÓN DE INTEGRIDAD DE RESEÑAS
# ============================================================

print("\n6. Validando integridad de la consolidación...")

if len(resenas_consolidadas) != filas_resenas_originales:
    raise ValueError(
        "La consolidación modificó la cantidad de reseñas."
    )

if resenas_consolidadas["recommendationid"].duplicated().any():
    raise ValueError(
        "Se detectaron RecommendationID duplicados después del JOIN."
    )

if resenas_consolidadas["recommendationid"].isna().any():
    raise ValueError(
        "Se detectaron RecommendationID nulos después del JOIN."
    )

print("Integridad de reseñas validada.")
print(f"Filas originales: {filas_resenas_originales:,}")
print(f"Filas consolidadas: {len(resenas_consolidadas):,}")


# ============================================================
# 7. CONSOLIDACIÓN INDEPENDIENTE DE NOVEDADES
# ============================================================

print("\n7. Preparando conjunto consolidado de novedades...")

novedades_consolidadas = novedades.copy()

if novedades_consolidadas["gid"].duplicated().any():
    raise ValueError(
        "Se detectaron GID duplicados en novedades."
    )

print(
    "Se conserva la tabla novedades_juegos sin unirla "
    "directamente con las reseñas."
)

print(f"Publicaciones conservadas: {len(novedades_consolidadas):,}")


# ============================================================
# 8. EXPORTACIÓN
# ============================================================

print("\n8. Exportando tablas consolidadas...")

resenas_consolidadas.to_parquet(
    SALIDA_RESENAS,
    index=False
)

novedades_consolidadas.to_parquet(
    SALIDA_NOVEDADES,
    index=False
)

print("Archivos exportados correctamente.")


# ============================================================
# 9. VERIFICACIÓN DE ARCHIVOS
# ============================================================

print("\n9. Verificando archivos exportados...")

resenas_verificacion = pd.read_parquet(SALIDA_RESENAS)
novedades_verificacion = pd.read_parquet(SALIDA_NOVEDADES)

if len(resenas_verificacion) != filas_resenas_originales:
    raise ValueError(
        "La verificación detectó una cantidad incorrecta de reseñas."
    )

if len(novedades_verificacion) != len(novedades):
    raise ValueError(
        "La verificación detectó una cantidad incorrecta de novedades."
    )

if resenas_verificacion["recommendationid"].duplicated().any():
    raise ValueError(
        "Hay RecommendationID duplicados en el archivo exportado."
    )


# ============================================================
# 10. INFORME FINAL
# ============================================================

print("\n" + "=" * 65)
print("RESULTADO - SCRIPT 6")
print("=" * 65)

print("\nRESEÑAS CONSOLIDADAS")
print(f"Filas: {len(resenas_verificacion):,}")
print(f"Columnas: {len(resenas_verificacion.columns):,}")
print(f"Juegos asociados: {coincidencias_juegos:,}")
print(f"Sin juego asociado: {sin_juego:,}")
print(f"Usuarios asociados: {coincidencias_usuarios:,}")
print(f"Sin usuario asociado: {sin_usuario:,}")

print("\nNOVEDADES CONSOLIDADAS")
print(f"Filas: {len(novedades_verificacion):,}")
print(f"Columnas: {len(novedades_verificacion.columns):,}")

print("\nARCHIVOS GENERADOS")
print(SALIDA_RESENAS)
print(SALIDA_NOVEDADES)

print("\n" + "=" * 65)
print("SCRIPT 6 FINALIZADO CORRECTAMENTE.")
print("=" * 65)
