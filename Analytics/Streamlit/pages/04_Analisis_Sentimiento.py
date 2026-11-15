import streamlit as st
import pandas as pd

from utils import mostrar_navegacion
from utils.data_loader import cargar_modelo, cargar_datasets
from utils.predicciones import predecir_sentimiento

st.set_page_config(
    page_title="Análisis de sentimiento",
    page_icon="💬",
    layout="wide"
)

mostrar_navegacion()

st.title("💬 Análisis de sentimiento")

st.markdown(
    """
    Análisis automatizado de opiniones de usuarios mediante
    TF-IDF y Linear SVM.

    El objetivo es identificar señales de satisfacción,
    problemas recurrentes y oportunidades de mejora de producto.
    """
)

# ============================================================
# 1. CARGA DEL MODELO
# ============================================================

try:
    modelo = cargar_modelo()
except Exception as error:
    st.error(
        f"No fue posible cargar el modelo: {error}"
    )
    st.stop()

# ============================================================
# 2. CLASIFICACION INDIVIDUAL
# ============================================================

st.divider()

st.subheader("Analizar una reseña")

texto = st.text_area(
    "Ingresar una reseña en inglés",
    height=180,
    placeholder="Write your game review here..."
)

if st.button(
    "Analizar reseña",
    type="primary"
):

    if not texto.strip():

        st.warning("Ingresá una reseña antes de analizar.")

    else:

        try:

            resultado = predecir_sentimiento(
                modelo,
                texto
            )

            sentimiento = resultado["sentimiento"]

            if sentimiento == "Positiva":

                st.success(
                    "Sentimiento detectado: POSITIVO"
                )

            else:

                st.error(
                    "Sentimiento detectado: NEGATIVO"
                )

            margen = resultado.get(
                "margen_decision"
            )

            if margen is not None:

                st.metric(
                    "Margen de decisión",
                    f"{margen:.4f}"
                )

                st.caption(
                    "El margen de decisión no es una probabilidad."
                )

            st.subheader("Interpretación empresarial")

            if sentimiento == "Positiva":

                st.markdown(
                    """
                    **Señal favorable**

                    La reseña contiene una opinión clasificada
                    como positiva por el modelo.

                    Recomendación: identificar atributos valorados
                    y analizar si aparecen de forma recurrente
                    en otras opiniones.
                    """
                )

            else:

                st.markdown(
                    """
                    **Señal de atención**

                    La reseña contiene una opinión clasificada
                    como negativa por el modelo.

                    Recomendación: investigar los problemas
                    descritos y determinar si requieren mejoras
                    de producto o comunicación.
                    """
                )

        except (TypeError, ValueError) as error:

            st.warning(str(error))

        except Exception as error:

            st.error(
                f"Error durante la predicción: {error}"
            )

# ============================================================
# 3. ANALISIS DE RESEÑAS DE LA BASE
# ============================================================

st.divider()

st.subheader("Exploración de reseñas disponibles")

st.markdown(
    """
    Esta sección permite consultar las reseñas reales de la muestra.
    La clasificación individual del modelo y la recomendación original
    de Steam son indicadores diferentes.
    """
)

try:

    datos = cargar_datasets()

    resenas = datos["resenas_dashboard"].copy()

    if not resenas.empty:

        if "voted_up" in resenas.columns:

            positivas = int(
                resenas["voted_up"].eq(True).sum()
            )

            negativas = int(
                resenas["voted_up"].eq(False).sum()
            )

            total = positivas + negativas

            porcentaje_positivo = (
                positivas / total * 100
                if total else 0
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Reseñas",
                f"{len(resenas):,}"
            )

            col2.metric(
                "Recomendaciones positivas",
                f"{porcentaje_positivo:.2f}%"
            )

            col3.metric(
                "Recomendaciones negativas",
                f"{negativas:,}"
            )

        # Filtros de consulta
        juegos = sorted(
            resenas["name"].dropna().unique().tolist()
        )

        juego = st.selectbox(
            "Filtrar por videojuego",
            ["Todos"] + juegos,
            key="sentimiento_juego"
        )

        tipo = st.selectbox(
            "Filtrar por recomendación original",
            ["Todas", "Positivas", "Negativas"],
            key="sentimiento_tipo"
        )

        filtradas = resenas.copy()

        if juego != "Todos":

            filtradas = filtradas[
                filtradas["name"] == juego
            ]

        if tipo == "Positivas":

            filtradas = filtradas[
                filtradas["voted_up"] == True
            ]

        elif tipo == "Negativas":

            filtradas = filtradas[
                filtradas["voted_up"] == False
            ]

        st.write(
            f"Reseñas encontradas: {len(filtradas):,}"
        )

        columnas = [
            c for c in [
                "name",
                "voted_up",
                "language_code",
                "review"
            ]
            if c in filtradas.columns
        ]

        st.dataframe(
            filtradas[columnas].head(100),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No hay reseñas disponibles.")

except Exception as error:

    st.warning(
        f"No fue posible cargar la exploración de reseñas: {error}"
    )

# ============================================================
# 4. RECOMENDACIONES DE USO DEL MODELO
# ============================================================

st.divider()

st.header("Aplicación empresarial del análisis de sentimiento")

tab1, tab2, tab3 = st.tabs([
    "Desarrolladores",
    "Publishers",
    "Inversores"
])

with tab1:

    st.markdown(
        """
        - Detectar problemas de experiencia.
        - Priorizar mejoras en función de las opiniones.
        - Monitorear cambios en la percepción después de actualizaciones.
        - Identificar atributos valorados por la comunidad.
        """
    )

with tab2:

    st.markdown(
        """
        - Monitorear riesgos reputacionales.
        - Identificar señales de aceptación o rechazo.
        - Evaluar la respuesta de la comunidad a campañas y lanzamientos.
        - Complementar estudios de mercado.
        """
    )

with tab3:

    st.markdown(
        """
        - Utilizar el sentimiento como indicador complementario.
        - Investigar riesgos de producto y reputación.
        - Contrastar las señales con métricas comerciales.
        - Evaluar tendencias de aceptación antes de tomar decisiones.
        """
    )

st.warning(
    """
    El modelo clasifica texto según patrones aprendidos durante
    el entrenamiento. No garantiza una interpretación perfecta,
    no identifica causalidad y no estima ventas ni rentabilidad.
    """
)

st.caption(
    "Modelo de clasificación: TF-IDF + Linear SVM."
)
