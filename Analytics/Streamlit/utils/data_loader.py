from pathlib import Path

import joblib
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
MODELS_DIR = BASE_DIR / "models"

MODEL_PATH = MODELS_DIR / "steam_linear_svm_tfidf_final.joblib"


# ------------------------------------------------------------
# CARGA DE DATASETS
# ------------------------------------------------------------

@st.cache_data
def cargar_datasets():

    archivos = {
        "resenas_dashboard": "resenas_dashboard.parquet",
        "resenas_cohortes": "resenas_cohortes.parquet",
        "kpis_generales": "kpis_generales.parquet",
        "resumen_cohortes": "resumen_cohortes.parquet",
        "actividad_mensual": "actividad_mensual.parquet",
        "ranking_juegos": "ranking_juegos.parquet"
    }

    datos = {}

    for nombre, archivo in archivos.items():

        ruta = DATA_DIR / archivo

        if not ruta.exists():
            raise FileNotFoundError(
                f"No se encontro el archivo: {ruta}"
            )

        datos[nombre] = pd.read_parquet(ruta)

    return datos


# ------------------------------------------------------------
# CARGA DEL MODELO
# ------------------------------------------------------------

@st.cache_resource
def cargar_modelo():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No se encontro el modelo: {MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)
