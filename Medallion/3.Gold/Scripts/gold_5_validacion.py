
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# ============================================================
# GOLD - SCRIPT 5: VALIDACION INTEGRAL
# ============================================================

BASE = Path("/content/Infraestructura-de-ciencia-de-datos/Medallion")
GOLD = BASE / "3.Gold" / "Data"
SILVER = BASE / "2.Silver" / "Data"

ARCHIVOS = {
    "dim_usuarios": GOLD / "dim_usuarios.parquet",
    "dim_juegos": GOLD / "dim_juegos.parquet",
    "dim_fecha": GOLD / "dim_fecha.parquet",
    "dim_idioma": GOLD / "dim_idioma.parquet",
    "dim_hardware": GOLD / "dim_hardware.parquet",
    "fact_resenas": GOLD / "fact_resenas.parquet",
    "fact_novedades": GOLD / "fact_novedades.parquet",
    "agg_juego_mes": GOLD / "agg_juego_mes.parquet"
}

SALIDAS = {
    "csv": GOLD / "validacion_gold.csv",
    "json": GOLD / "validacion_gold.json",
    "txt": GOLD / "validacion_gold.txt"
}

print("=" * 70)
print("GOLD - SCRIPT 5: VALIDACION INTEGRAL")
print("=" * 70)

# ------------------------------------------------------------
# 1. REGISTRO DE CONTROLES
# ------------------------------------------------------------

controles = []

def registrar(nombre, resultado, detalle, tipo="CONTROL"):
    controles.append({
        "tipo": tipo,
        "control": nombre,
        "resultado": "OK" if resultado else "ERROR",
        "detalle": str(detalle)
    })

def advertir(nombre, detalle):
    controles.append({
        "tipo": "ADVERTENCIA",
        "control": nombre,
        "resultado": "ADVERTENCIA",
        "detalle": str(detalle)
    })

# ------------------------------------------------------------
# 2. EXISTENCIA Y CARGA DE ARCHIVOS
# ------------------------------------------------------------

datos = {}

print("\n1. CARGA DE ARCHIVOS GOLD")

for nombre, ruta in ARCHIVOS.items():
    if not ruta.exists():
        registrar(
            f"Existencia de {nombre}",
            False,
            f"No se encontró: {ruta}"
        )
        continue

    df = pd.read_parquet(ruta)
    datos[nombre] = df

    registrar(
        f"Existencia de {nombre}",
        True,
        f"{len(df):,} filas y {len(df.columns)} columnas"
    )

    print(f"{nombre}: {len(df):,} filas")

if len(datos) != len(ARCHIVOS):
    raise FileNotFoundError(
        "Faltan archivos Gold. Revisá los errores de existencia."
    )

# ------------------------------------------------------------
# 3. VALIDACION DE DIMENSIONES
# ------------------------------------------------------------

print("\n2. VALIDACION DE DIMENSIONES")

DIMENSIONES = {
    "dim_usuarios": "user_key",
    "dim_juegos": "game_key",
    "dim_fecha": "date_key",
    "dim_idioma": "language_key",
    "dim_hardware": "hardware_key"
}

for nombre, pk in DIMENSIONES.items():
    df = datos[nombre]

    registrar(
        f"{nombre}: columna PK",
        pk in df.columns,
        f"Columna requerida: {pk}"
    )

    if pk not in df.columns:
        continue

    sin_nulos = not df[pk].isna().any()
    sin_duplicados = not df[pk].duplicated().any()
    no_negativas = pd.to_numeric(
        df[pk], errors="coerce"
    ).ge(0).all()

    registrar(
        f"{nombre}: PK sin nulos",
        sin_nulos,
        f"Nulos: {int(df[pk].isna().sum())}"
    )

    registrar(
        f"{nombre}: PK sin duplicados",
        sin_duplicados,
        f"Duplicados: {int(df[pk].duplicated().sum())}"
    )

    registrar(
        f"{nombre}: PK no negativas",
        no_negativas,
        "Las claves deben ser enteros no negativos."
    )

    tiene_unknown = (
        pd.to_numeric(df[pk], errors="coerce") == 0
    ).any()

    registrar(
        f"{nombre}: registro desconocido",
        tiene_unknown,
        "Se requiere una fila con clave sustituta 0."
    )

# ------------------------------------------------------------
# 4. VALIDACION DE TABLAS DE HECHOS
# ------------------------------------------------------------

print("\n3. VALIDACION DE TABLAS DE HECHOS")

def validar_hecho(nombre, identificador, claves):
    df = datos[nombre]

    registrar(
        f"{nombre}: identificador presente",
        identificador in df.columns,
        identificador
    )

    if identificador in df.columns:
        registrar(
            f"{nombre}: identificador sin nulos",
            not df[identificador].isna().any(),
            f"Nulos: {int(df[identificador].isna().sum())}"
        )

        registrar(
            f"{nombre}: identificador único",
            not df[identificador].duplicated().any(),
            f"Duplicados: {int(df[identificador].duplicated().sum())}"
        )

    for columna, dimension, pk in claves:
        if columna not in df.columns:
            registrar(
                f"{nombre}: columna {columna}",
                False,
                "No existe la clave foránea."
            )
            continue

        valores = pd.to_numeric(
            df[columna], errors="coerce"
        )

        registrar(
            f"{nombre}: {columna} sin nulos",
            not valores.isna().any(),
            f"Nulos: {int(valores.isna().sum())}"
        )

        registrar(
            f"{nombre}: {columna} no negativa",
            valores.ge(0).all(),
            f"Valores negativos: {int((valores < 0).sum())}"
        )

        if dimension not in datos or pk not in datos[dimension].columns:
            registrar(
                f"{nombre}: integridad {columna}",
                False,
                f"No se pudo consultar {dimension}.{pk}"
            )
            continue

        claves_validas = set(
            pd.to_numeric(
                datos[dimension][pk],
                errors="coerce"
            ).dropna().astype("int64")
        )

        claves_hecho = set(
            valores.dropna().astype("int64")
        )

        faltantes = claves_hecho - claves_validas

        registrar(
            f"{nombre}: integridad referencial {columna}",
            len(faltantes) == 0,
            f"Claves sin correspondencia: {len(faltantes)}"
        )

        desconocidos = int((valores == 0).sum())

        if desconocidos > 0:
            advertir(
                f"{nombre}: {columna} desconocida",
                f"{desconocidos:,} registros asociados a clave 0."
            )

validar_hecho(
    "fact_resenas",
    "recommendationid",
    [
        ("user_key", "dim_usuarios", "user_key"),
        ("game_key", "dim_juegos", "game_key"),
        ("date_key", "dim_fecha", "date_key"),
        ("language_key", "dim_idioma", "language_key"),
        ("hardware_key", "dim_hardware", "hardware_key")
    ]
)

validar_hecho(
    "fact_novedades",
    "gid",
    [
        ("game_key", "dim_juegos", "game_key"),
        ("date_key", "dim_fecha", "date_key")
    ]
)

# ------------------------------------------------------------
# 5. VALIDACION DE AGREGACIONES
# ------------------------------------------------------------

print("\n4. VALIDACION DE AGREGACIONES")

resenas = datos["fact_resenas"]
novedades = datos["fact_novedades"]
agg = datos["agg_juego_mes"]
fechas = datos["dim_fecha"]

columnas_agg = {
    "game_key",
    "year",
    "month",
    "month_key",
    "cantidad_resenas",
    "cantidad_novedades"
}

faltantes = columnas_agg - set(agg.columns)

registrar(
    "Agregación: estructura",
    len(faltantes) == 0,
    f"Columnas faltantes: {sorted(faltantes)}"
)

if not faltantes:
    registrar(
        "Agregación: combinaciones únicas",
        not agg.duplicated(
            ["game_key", "year", "month"]
        ).any(),
        "No debe haber más de una fila por juego y mes."
    )

    registrar(
        "Agregación: valores sin nulos",
        not agg[list(columnas_agg)].isna().any().any(),
        "Las columnas de control no deben contener nulos."
    )

    total_resenas = int(agg["cantidad_resenas"].sum())
    total_novedades = int(agg["cantidad_novedades"].sum())

    registrar(
        "Agregación: total de reseñas",
        total_resenas == len(resenas),
        f"Agregadas: {total_resenas:,} | Fact: {len(resenas):,}"
    )

    registrar(
        "Agregación: total de novedades",
        total_novedades == len(novedades),
        f"Agregadas: {total_novedades:,} | Fact: {len(novedades):,}"
    )

    # Reconstruir agregación esperada desde las tablas de hechos.
    mapa_fechas = fechas[
        ["date_key", "year", "month"]
    ].copy()

    for columna in ["date_key", "year", "month"]:
        mapa_fechas[columna] = pd.to_numeric(
            mapa_fechas[columna], errors="coerce"
        )

    def recalcular(df, identificador, nombre):
        trabajo = df[
            [identificador, "game_key", "date_key"]
        ].copy()

        trabajo["game_key"] = pd.to_numeric(
            trabajo["game_key"], errors="coerce"
        )

        trabajo["date_key"] = pd.to_numeric(
            trabajo["date_key"], errors="coerce"
        )

        trabajo = trabajo.merge(
            mapa_fechas,
            on="date_key",
            how="left",
            validate="many_to_one"
        )

        trabajo["year"] = trabajo["year"].fillna(0).astype("int64")
        trabajo["month"] = trabajo["month"].fillna(0).astype("int64")
        trabajo["game_key"] = trabajo["game_key"].astype("int64")

        trabajo["month_key"] = (
            trabajo["year"] * 100 + trabajo["month"]
        )

        return (
            trabajo.groupby(
                ["game_key", "year", "month", "month_key"],
                as_index=False
            )
            .size()
            .rename(columns={"size": nombre})
        )

    esperado_resenas = recalcular(
        resenas, "recommendationid", "cantidad_resenas"
    )

    esperado_novedades = recalcular(
        novedades, "gid", "cantidad_novedades"
    )

    esperado = esperado_resenas.merge(
        esperado_novedades,
        on=["game_key", "year", "month", "month_key"],
        how="outer",
        validate="one_to_one"
    ).fillna(0)

    esperado["cantidad_resenas"] = (
        esperado["cantidad_resenas"].astype("int64")
    )
    esperado["cantidad_novedades"] = (
        esperado["cantidad_novedades"].astype("int64")
    )

    claves = ["game_key", "year", "month", "month_key"]

    actual = agg[
        claves + ["cantidad_resenas", "cantidad_novedades"]
    ].copy()

    comparacion = actual.merge(
        esperado,
        on=claves,
        how="outer",
        suffixes=("_actual", "_esperado"),
        indicator=True
    )

    diferencias = comparacion[
        (comparacion["_merge"] != "both") |
        (
            comparacion["cantidad_resenas_actual"] !=
            comparacion["cantidad_resenas_esperado"]
        ) |
        (
            comparacion["cantidad_novedades_actual"] !=
            comparacion["cantidad_novedades_esperado"]
        )
    ]

    registrar(
        "Agregación: consistencia con tablas de hechos",
        len(diferencias) == 0,
        f"Combinaciones con diferencias: {len(diferencias)}"
    )

# ------------------------------------------------------------
# 6. COMPARACION CON SILVER
# ------------------------------------------------------------

print("\n5. COMPARACION CON SILVER")

FUENTES_SILVER = [
    (
        "resenas.parquet",
        "fact_resenas",
        "recommendationid"
    ),
    (
        "novedades_consolidadas.parquet",
        "fact_novedades",
        "gid"
    )
]

for archivo, hecho, identificador in FUENTES_SILVER:
    ruta = SILVER / archivo

    if not ruta.exists():
        advertir(
            f"Comparación Silver: {archivo}",
            "No se encontró el archivo fuente; comparación omitida."
        )
        continue

    silver = pd.read_parquet(ruta)
    gold = datos[hecho]

    if identificador not in silver.columns:
        advertir(
            f"Comparación Silver: {archivo}",
            f"No existe la columna {identificador}."
        )
        continue

    ids_silver = set(
        silver[identificador].dropna().astype(str)
    )

    ids_gold = set(
        gold[identificador].dropna().astype(str)
    )

    faltan_gold = ids_silver - ids_gold
    sobran_gold = ids_gold - ids_silver

    registrar(
        f"{hecho}: identificadores conservados desde Silver",
        len(faltan_gold) == 0 and len(sobran_gold) == 0,
        (
            f"Silver: {len(ids_silver):,} | Gold: {len(ids_gold):,} | "
            f"Faltantes: {len(faltan_gold)} | "
            f"Adicionales: {len(sobran_gold)}"
        )
    )

# ------------------------------------------------------------
# 7. RESUMEN DE CALIDAD
# ------------------------------------------------------------

print("\n6. RESUMEN DE VALIDACIÓN")

df_controles = pd.DataFrame(controles)

total_ok = int((df_controles["resultado"] == "OK").sum())
total_errores = int((df_controles["resultado"] == "ERROR").sum())
total_advertencias = int(
    (df_controles["resultado"] == "ADVERTENCIA").sum()
)

estado = (
    "APROBADO"
    if total_errores == 0 and total_advertencias == 0
    else "APROBADO CON ADVERTENCIAS"
    if total_errores == 0
    else "RECHAZADO"
)

print(f"Controles OK: {total_ok}")
print(f"Errores: {total_errores}")
print(f"Advertencias: {total_advertencias}")
print(f"ESTADO FINAL: {estado}")

# ------------------------------------------------------------
# 8. GUARDAR INFORMES
# ------------------------------------------------------------

df_controles.to_csv(
    SALIDAS["csv"],
    index=False,
    encoding="utf-8-sig"
)

informe = {
    "fecha_validacion": datetime.now().isoformat(),
    "capa": "Gold",
    "estado": estado,
    "resumen": {
        "controles_ok": total_ok,
        "errores": total_errores,
        "advertencias": total_advertencias
    },
    "archivos": {
        nombre: {
            "filas": len(df),
            "columnas": len(df.columns)
        }
        for nombre, df in datos.items()
    },
    "controles": controles
}

with open(SALIDAS["json"], "w", encoding="utf-8") as archivo:
    json.dump(
        informe,
        archivo,
        ensure_ascii=False,
        indent=4,
        default=str
    )

lineas = [
    "=" * 70,
    "INFORME DE VALIDACIÓN INTEGRAL - CAPA GOLD",
    "=" * 70,
    f"Fecha: {informe['fecha_validacion']}",
    f"Estado: {estado}",
    "",
    f"Controles OK: {total_ok}",
    f"Errores: {total_errores}",
    f"Advertencias: {total_advertencias}",
    "",
    "DETALLE DE CONTROLES",
    "-" * 70
]

for control in controles:
    lineas.append(
        f"[{control['resultado']}] "
        f"{control['control']}: {control['detalle']}"
    )

lineas.extend([
    "",
    "=" * 70,
    f"RESULTADO FINAL: {estado}",
    "=" * 70
])

SALIDAS["txt"].write_text(
    "\n".join(lineas),
    encoding="utf-8"
)

print("\n7. INFORMES GENERADOS")

for tipo, ruta in SALIDAS.items():
    print(f"{tipo.upper()}: {ruta}")

print("\n" + "=" * 70)
print(f"VALIDACIÓN GOLD FINALIZADA: {estado}")
print("=" * 70)
