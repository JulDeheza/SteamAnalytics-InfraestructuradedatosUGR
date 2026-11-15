
"""
CAPA SILVER - SCRIPT 7: VALIDACION INTEGRAL

Audita los archivos Silver:
- Estructura y existencia
- Cantidad de registros
- Claves primarias
- Nulos y duplicados
- Relaciones entre tablas
- Integridad de consolidaciones
- Recortes temporales 2020-2025
- Comparacion de cantidades Bronze vs Silver

No modifica ni elimina datos.
Genera informes CSV, JSON y TXT.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# 1. CONFIGURACION
# ============================================================

ROOT = Path("/content/Infraestructura-de-ciencia-de-datos")

BRONZE_DATA = ROOT / "Medallion" / "1.Bronze" / "Data"
SILVER_DATA = ROOT / "Medallion" / "2.Silver" / "Data"
SCRIPTS_DATA = ROOT / "Medallion" / "2.Silver" / "Scripts"

RECORTES_DATA = SILVER_DATA / "recortes"

SILVER_DATA.mkdir(parents=True, exist_ok=True)
SCRIPTS_DATA.mkdir(parents=True, exist_ok=True)

ARCHIVOS = {
    "juegos": SILVER_DATA / "juegos.parquet",
    "usuarios": SILVER_DATA / "usuarios.parquet",
    "novedades": SILVER_DATA / "novedades.parquet",
    "novedades_juegos": SILVER_DATA / "novedades_juegos.parquet",
    "resenas": SILVER_DATA / "resenas.parquet",
    "resenas_consolidadas": SILVER_DATA / "resenas_consolidadas.parquet",
    "novedades_consolidadas": SILVER_DATA / "novedades_consolidadas.parquet"
}

ARCHIVOS_BRONZE = {
    "juegos": BRONZE_DATA / "juegos.json",
    "usuarios": BRONZE_DATA / "usuarios.json",
    "novedades": BRONZE_DATA / "novedades.json",
    "resenas": BRONZE_DATA / "resenas.json"
}

SALIDA_CSV = SILVER_DATA / "validacion_silver.csv"
SALIDA_JSON = SILVER_DATA / "validacion_silver.json"
SALIDA_TXT = SILVER_DATA / "validacion_silver.txt"


# ============================================================
# 2. SISTEMA DE REGISTRO DE CONTROLES
# ============================================================

resultados = []

def registrar(
    control,
    estado,
    detalle,
    categoria="GENERAL"
):
    resultados.append({
        "categoria": categoria,
        "control": control,
        "estado": estado,
        "detalle": str(detalle)
    })

    simbolo = {
        "OK": "[OK]",
        "ADVERTENCIA": "[ADVERTENCIA]",
        "ERROR": "[ERROR]"
    }.get(estado, "[INFO]")

    print(f"{simbolo} {control}: {detalle}")


def comprobar(
    condicion,
    control,
    detalle_ok,
    detalle_error,
    categoria="GENERAL"
):
    if condicion:
        registrar(
            control,
            "OK",
            detalle_ok,
            categoria
        )
        return True

    registrar(
        control,
        "ERROR",
        detalle_error,
        categoria
    )
    return False


# ============================================================
# 3. INICIO
# ============================================================

print("=" * 70)
print("CAPA SILVER - SCRIPT 7: VALIDACION INTEGRAL")
print("=" * 70)

print("\nFecha de auditoria:")
print(datetime.now(timezone.utc).isoformat())

print("\n1. VERIFICACION DE ARCHIVOS")


# ============================================================
# 4. VERIFICAR EXISTENCIA DE PARQUET
# ============================================================

for nombre, ruta in ARCHIVOS.items():

    comprobar(
        ruta.exists(),
        f"Existencia de {nombre}",
        f"Archivo encontrado: {ruta.name}",
        f"No existe el archivo: {ruta}",
        "ARCHIVOS"
    )

for anio in range(2020, 2026):

    ruta = RECORTES_DATA / f"novedades_{anio}.parquet"

    comprobar(
        ruta.exists(),
        f"Existencia recorte {anio}",
        f"Recorte encontrado: {ruta.name}",
        f"No existe el recorte: {ruta}",
        "ARCHIVOS"
    )


# ============================================================
# 5. CARGA DE TABLAS
# ============================================================

print("\n2. CARGA DE TABLAS SILVER")

tablas = {}

for nombre, ruta in ARCHIVOS.items():

    if ruta.exists():

        try:
            tablas[nombre] = pd.read_parquet(ruta)

            registrar(
                f"Carga de {nombre}",
                "OK",
                (
                    f"{len(tablas[nombre]):,} filas; "
                    f"{len(tablas[nombre].columns):,} columnas"
                ),
                "CARGA"
            )

        except Exception as error:

            registrar(
                f"Carga de {nombre}",
                "ERROR",
                str(error),
                "CARGA"
            )


# Carga de recortes
recortes = {}

for anio in range(2020, 2026):

    ruta = RECORTES_DATA / f"novedades_{anio}.parquet"

    if ruta.exists():

        try:
            recortes[anio] = pd.read_parquet(ruta)

            registrar(
                f"Carga recorte {anio}",
                "OK",
                f"{len(recortes[anio]):,} filas",
                "CARGA"
            )

        except Exception as error:

            registrar(
                f"Carga recorte {anio}",
                "ERROR",
                str(error),
                "CARGA"
            )


# ============================================================
# 6. ESTRUCTURA Y CLAVES PRINCIPALES
# ============================================================

print("\n3. VALIDACION DE ESTRUCTURA Y CLAVES")

claves = {
    "juegos": "appid",
    "usuarios": "steamid",
    "novedades": "gid",
    "novedades_juegos": "gid",
    "resenas": "recommendationid",
    "resenas_consolidadas": "recommendationid",
    "novedades_consolidadas": "gid"
}

for nombre, clave in claves.items():

    if nombre not in tablas:
        continue

    df = tablas[nombre]

    if clave not in df.columns:

        registrar(
            f"Columna clave {nombre}",
            "ERROR",
            f"No existe la columna {clave}",
            "ESTRUCTURA"
        )
        continue

    nulos = int(df[clave].isna().sum())
    duplicados = int(df[clave].duplicated().sum())

    comprobar(
        nulos == 0,
        f"Nulos en {nombre}.{clave}",
        "Sin valores nulos",
        f"Se encontraron {nulos:,} valores nulos",
        "CLAVES"
    )

    comprobar(
        duplicados == 0,
        f"Duplicados en {nombre}.{clave}",
        "Clave única",
        f"Se encontraron {duplicados:,} duplicados",
        "CLAVES"
    )


# ============================================================
# 7. CONTROL DE CANTIDADES
# ============================================================

print("\n4. CONTROL DE CANTIDADES")

cantidades_esperadas = {
    "juegos": 5000,
    "usuarios": 38999,
    "novedades": 5039,
    "novedades_juegos": 5039,
    "resenas": 46990,
    "resenas_consolidadas": 46990,
    "novedades_consolidadas": 5039
}

for nombre, esperado in cantidades_esperadas.items():

    if nombre not in tablas:
        continue

    actual = len(tablas[nombre])

    comprobar(
        actual == esperado,
        f"Cantidad de {nombre}",
        f"{actual:,} registros, cantidad esperada",
        (
            f"Se esperaban {esperado:,} registros "
            f"y se encontraron {actual:,}"
        ),
        "CANTIDADES"
    )


# ============================================================
# 8. COMPARACION BRONZE VS SILVER
# ============================================================

print("\n5. COMPARACION BRONZE VS SILVER")


def contar_bronze(nombre, ruta):

    if not ruta.exists():
        return None

    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if nombre == "juegos":
        return len(contenido["apps"])

    if nombre == "usuarios":
        return len(contenido["users"])

    if nombre == "novedades":
        return len(contenido)

    if nombre == "resenas":
        return len(contenido)

    return None


comparaciones = {
    "juegos": "juegos",
    "usuarios": "usuarios",
    "novedades": "novedades",
    "resenas": "resenas"
}

for nombre_silver, nombre_bronze in comparaciones.items():

    ruta = ARCHIVOS_BRONZE[nombre_bronze]

    if nombre_silver not in tablas:
        continue

    try:

        cantidad_bronze = contar_bronze(
            nombre_bronze,
            ruta
        )

        cantidad_silver = len(tablas[nombre_silver])

        if cantidad_bronze is None:
            raise ValueError("No se pudo determinar la cantidad Bronze.")

        comprobar(
            cantidad_bronze == cantidad_silver,
            f"Bronze vs Silver: {nombre_silver}",
            (
                f"Bronze: {cantidad_bronze:,}; "
                f"Silver: {cantidad_silver:,}"
            ),
            (
                f"Bronze: {cantidad_bronze:,}; "
                f"Silver: {cantidad_silver:,}"
            ),
            "BRONZE_SILVER"
        )

    except Exception as error:

        registrar(
            f"Comparacion Bronze: {nombre_silver}",
            "ERROR",
            str(error),
            "BRONZE_SILVER"
        )


# ============================================================
# 9. VALIDACION DE RELACIONES
# ============================================================

print("\n6. VALIDACION DE RELACIONES")

if "resenas" in tablas and "resenas_consolidadas" in tablas:

    base = tablas["resenas"]
    consolidada = tablas["resenas_consolidadas"]

    ids_base = set(
        base["recommendationid"].astype("string")
    )

    ids_consolidados = set(
        consolidada["recommendationid"].astype("string")
    )

    comprobar(
        ids_base == ids_consolidados,
        "Integridad de RecommendationID",
        "Todas las reseñas originales están conservadas",
        "Hay identificadores faltantes o adicionales",
        "RELACIONES"
    )

    if "game_match_status" in consolidada.columns:

        sin_juego = int(
            (consolidada["game_match_status"] == "NO_MATCH").sum()
        )

        comprobar(
            sin_juego == 0,
            "Relacion reseñas-juegos",
            "Todas las reseñas tienen juego asociado",
            f"Hay {sin_juego:,} reseñas sin juego asociado",
            "RELACIONES"
        )

    else:

        registrar(
            "Relacion reseñas-juegos",
            "ERROR",
            "No existe game_match_status",
            "RELACIONES"
        )

    if "user_match_status" in consolidada.columns:

        sin_usuario = int(
            (consolidada["user_match_status"] == "NO_MATCH").sum()
        )

        asociados = int(
            (consolidada["user_match_status"] == "MATCH").sum()
        )

        if sin_usuario == 0:

            registrar(
                "Relacion reseñas-usuarios",
                "OK",
                f"Todas las reseñas tienen usuario asociado ({asociados:,})",
                "RELACIONES"
            )

        else:

            registrar(
                "Relacion reseñas-usuarios",
                "ADVERTENCIA",
                (
                    f"{sin_usuario:,} reseña(s) sin usuario asociado; "
                    f"{asociados:,} asociadas. "
                    "Los registros se conservaron."
                ),
                "RELACIONES"
            )

        comprobar(
            asociados + sin_usuario == len(consolidada),
            "Consistencia estados de usuarios",
            "Todos los registros tienen estado de relación",
            "Los estados no coinciden con la cantidad de reseñas",
            "RELACIONES"
        )

    else:

        registrar(
            "Relacion reseñas-usuarios",
            "ERROR",
            "No existe user_match_status",
            "RELACIONES"
        )


# ============================================================
# 10. VALIDACION DE NOVEDADES
# ============================================================

print("\n7. VALIDACION DE NOVEDADES")

if (
    "novedades_juegos" in tablas
    and "novedades_consolidadas" in tablas
):

    original = tablas["novedades_juegos"]
    consolidada = tablas["novedades_consolidadas"]

    gids_originales = set(
        original["gid"].astype("string")
    )

    gids_consolidados = set(
        consolidada["gid"].astype("string")
    )

    comprobar(
        gids_originales == gids_consolidados,
        "Integridad de GID",
        "Todos los GID originales están conservados",
        "Hay GID faltantes o adicionales",
        "NOVEDADES"
    )


# ============================================================
# 11. VALIDACION DE RECORTES 2020-2025
# ============================================================

print("\n8. VALIDACION DE RECORTES TEMPORALES")

conteos_referencia = {
    2020: 949,
    2021: 1272,
    2022: 847,
    2023: 789,
    2024: 627,
    2025: 555
}

gids_recortes = []
total_recortes = 0

for anio, df in recortes.items():

    total_recortes += len(df)

    if "gid" not in df.columns:

        registrar(
            f"Clave GID recorte {anio}",
            "ERROR",
            "No existe columna gid",
            "RECORTES"
        )
        continue

    comprobar(
        df["gid"].notna().all(),
        f"GID no nulos recorte {anio}",
        "Todos los GID están completos",
        "Hay GID nulos",
        "RECORTES"
    )

    comprobar(
        not df["gid"].duplicated().any(),
        f"GID únicos recorte {anio}",
        "No hay GID duplicados",
        "Se encontraron GID duplicados",
        "RECORTES"
    )

    conteo_esperado = conteos_referencia[anio]

    comprobar(
        len(df) == conteo_esperado,
        f"Cantidad recorte {anio}",
        f"{len(df):,} registros",
        (
            f"Se esperaban {conteo_esperado:,} "
            f"y se encontraron {len(df):,}"
        ),
        "RECORTES"
    )

    if "year" in df.columns:

        anios_presentes = pd.to_numeric(
            df["year"],
            errors="coerce"
        ).dropna().unique()

        comprobar(
            len(anios_presentes) == 1
            and int(anios_presentes[0]) == anio,
            f"Consistencia temporal {anio}",
            f"Todos los registros pertenecen a {anio}",
            f"Se encontraron años inesperados: {anios_presentes}",
            "RECORTES"
        )

    elif "date_parsed" in df.columns:

        fechas = pd.to_datetime(
            df["date_parsed"],
            errors="coerce",
            utc=True
        )

        comprobar(
            fechas.dropna().dt.year.eq(anio).all(),
            f"Consistencia temporal {anio}",
            f"Las fechas corresponden a {anio}",
            "Se encontraron fechas de otro año o fechas inválidas",
            "RECORTES"
        )

    else:

        registrar(
            f"Consistencia temporal {anio}",
            "ADVERTENCIA",
            "No se encontró year ni date_parsed para comprobar el período",
            "RECORTES"
        )

    gids_recortes.extend(
        df["gid"].dropna().astype("string").tolist()
    )


# No debe haber GID repetidos entre distintos recortes
comprobar(
    len(gids_recortes) == len(set(gids_recortes)),
    "GID únicos entre recortes",
    "No hay publicaciones repetidas entre años",
    "Hay publicaciones repetidas entre distintos recortes",
    "RECORTES"
)

if "novedades_juegos" in tablas:

    novedades_base = tablas["novedades_juegos"]

    if "year" in novedades_base.columns:

        anios = pd.to_numeric(
            novedades_base["year"],
            errors="coerce"
        )

        periodo = novedades_base[
            anios.between(2020, 2025)
        ]

        gids_periodo = set(
            periodo["gid"].astype("string")
        )

        gids_recortados = set(gids_recortes)

        comprobar(
            gids_periodo == gids_recortados,
            "Cobertura total de recortes",
            (
                f"Los recortes cubren las {len(gids_periodo):,} "
                "publicaciones del período"
            ),
            (
                f"Base del período: {len(gids_periodo):,}; "
                f"recortes: {len(gids_recortados):,}"
            ),
            "RECORTES"
        )

    else:

        registrar(
            "Cobertura total de recortes",
            "ADVERTENCIA",
            "No se encontró columna year en novedades_juegos",
            "RECORTES"
        )

comprobar(
    total_recortes == 5039,
    "Total de recortes",
    f"{total_recortes:,} publicaciones",
    f"Se encontraron {total_recortes:,} publicaciones en recortes",
    "RECORTES"
)


# ============================================================
# 12. ANALISIS DE NULOS
# ============================================================

print("\n9. ANALISIS DE VALORES NULOS")

for nombre, df in tablas.items():

    total_nulos = int(df.isna().sum().sum())

    columnas_con_nulos = int(
        (df.isna().sum() > 0).sum()
    )

    registrar(
        f"Nulos en {nombre}",
        "OK",
        (
            f"{total_nulos:,} celdas nulas "
            f"en {columnas_con_nulos:,} columnas. "
            "Se informan sin eliminarlos."
        ),
        "NULOS"
    )


# ============================================================
# 13. TIPOS DE DATOS Y FECHAS
# ============================================================

print("\n10. VALIDACION DE FECHAS")

for nombre in [
    "usuarios",
    "novedades",
    "resenas",
    "resenas_consolidadas"
]:

    if nombre not in tablas:
        continue

    df = tablas[nombre]

    columnas_fecha = [
        columna for columna in df.columns
        if columna.endswith("_parsed")
    ]

    for columna in columnas_fecha:

        fechas = pd.to_datetime(
            df[columna],
            errors="coerce",
            utc=True
        )

        valores_originales = int(df[columna].notna().sum())
        valores_validos = int(fechas.notna().sum())

        if valores_validos == valores_originales:

            registrar(
                f"Fechas {nombre}.{columna}",
                "OK",
                f"{valores_validos:,} fechas válidas",
                "FECHAS"
            )

        else:

            registrar(
                f"Fechas {nombre}.{columna}",
                "ADVERTENCIA",
                (
                    f"{valores_validos:,} fechas válidas "
                    f"de {valores_originales:,} valores no nulos"
                ),
                "FECHAS"
            )


# ============================================================
# 14. RESUMEN DE RESULTADOS
# ============================================================

print("\n11. GENERANDO INFORME FINAL")

df_resultados = pd.DataFrame(resultados)

cantidad_ok = int(
    (df_resultados["estado"] == "OK").sum()
)

cantidad_advertencias = int(
    (df_resultados["estado"] == "ADVERTENCIA").sum()
)

cantidad_errores = int(
    (df_resultados["estado"] == "ERROR").sum()
)

if cantidad_errores > 0:
    estado_general = "NO APROBADO"
elif cantidad_advertencias > 0:
    estado_general = "APROBADO CON ADVERTENCIAS"
else:
    estado_general = "APROBADO"


# ============================================================
# 15. EXPORTACION DE INFORMES
# ============================================================

df_resultados.to_csv(
    SALIDA_CSV,
    index=False,
    encoding="utf-8-sig"
)

informe_json = {
    "fecha_auditoria_utc": datetime.now(
        timezone.utc
    ).isoformat(),
    "capa": "SILVER",
    "estado_general": estado_general,
    "controles_ok": cantidad_ok,
    "advertencias": cantidad_advertencias,
    "errores": cantidad_errores,
    "resultados": resultados
}

with open(
    SALIDA_JSON,
    "w",
    encoding="utf-8"
) as archivo:

    json.dump(
        informe_json,
        archivo,
        ensure_ascii=False,
        indent=4,
        default=str
    )


lineas = []

lineas.append("=" * 70)
lineas.append("INFORME DE VALIDACION - CAPA SILVER")
lineas.append("=" * 70)

lineas.append(
    f"Fecha UTC: {informe_json['fecha_auditoria_utc']}"
)

lineas.append(f"Estado general: {estado_general}")
lineas.append(f"Controles OK: {cantidad_ok}")
lineas.append(f"Advertencias: {cantidad_advertencias}")
lineas.append(f"Errores: {cantidad_errores}")

lineas.append("")
lineas.append("DETALLE DE CONTROLES")
lineas.append("-" * 70)

for resultado in resultados:

    lineas.append(
        f"[{resultado['estado']}] "
        f"{resultado['categoria']} - "
        f"{resultado['control']}: "
        f"{resultado['detalle']}"
    )

lineas.append("")
lineas.append("=" * 70)

with open(
    SALIDA_TXT,
    "w",
    encoding="utf-8"
) as archivo:

    archivo.write("\n".join(lineas))


# ============================================================
# 16. RESULTADO FINAL
# ============================================================

print("\n" + "=" * 70)
print("RESULTADO FINAL - AUDITORIA SILVER")
print("=" * 70)

print(f"Estado general: {estado_general}")
print(f"Controles correctos: {cantidad_ok}")
print(f"Advertencias: {cantidad_advertencias}")
print(f"Errores: {cantidad_errores}")

print("\nINFORMES GENERADOS:")
print(SALIDA_CSV)
print(SALIDA_JSON)
print(SALIDA_TXT)

print("\n" + "=" * 70)

if cantidad_errores > 0:

    print("VALIDACION FINALIZADA CON ERRORES.")
    print("Revisar el informe antes de comenzar Gold.")

elif cantidad_advertencias > 0:

    print("SILVER APROBADA CON ADVERTENCIAS.")
    print("Revisar las observaciones antes de comenzar Gold.")

else:

    print("SILVER VALIDADA CORRECTAMENTE.")
    print("CAPA SILVER LISTA PARA GOLD.")

print("=" * 70)
