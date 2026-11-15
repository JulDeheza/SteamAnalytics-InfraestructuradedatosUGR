import streamlit as st
import pandas as pd

from utils import mostrar_navegacion
from utils.data_loader import cargar_datasets
from utils.visualizaciones import (
    grafico_sentimiento,
    grafico_actividad_mensual,
    grafico_ranking_juegos
)

st.set_page_config(
    page_title="Análisis general",
    page_icon="📊",
    layout="wide"
)

mostrar_navegacion()

# ============================================================
# 1. CARGA Y PREPARACION
# ============================================================

datos = cargar_datasets()

resenas = datos["resenas_dashboard"].copy()

resenas["fecha_analisis"] = pd.to_datetime(
    resenas["timestamp_created_parsed"],
    errors="coerce",
    utc=True
)

resenas = resenas.dropna(
    subset=["fecha_analisis"]
)

st.title("📊 Análisis general")

st.markdown(
    """
    Diagnóstico general del mercado de videojuegos de Steam.

    Identificamos señales de demanda, aceptación, participación
    y oportunidades de mejora para desarrolladores, publishers
    e inversores.
    """
)

st.divider()

if resenas.empty:
    st.warning("No hay reseñas con fechas válidas.")
    st.stop()

# ============================================================
# 2. FILTROS
# ============================================================

st.subheader("Filtros de análisis")

fecha_min = resenas["fecha_analisis"].min().date()
fecha_max = resenas["fecha_analisis"].max().date()

col1, col2 = st.columns(2)

with col1:
    periodo = st.date_input(
        "Período de publicación de reseñas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
        format="DD/MM/YYYY"
    )

with col2:
    idiomas = sorted(
        resenas["language_code"].dropna().unique().tolist()
    )

    idioma = st.selectbox(
        "Idioma",
        ["Todos"] + idiomas
    )

col3, col4 = st.columns(2)

with col3:
    juegos = sorted(
        resenas["name"].dropna().unique().tolist()
    )

    juego = st.selectbox(
        "Videojuego",
        ["Todos"] + juegos
    )

with col4:
    tipo = st.selectbox(
        "Tipo de recomendación",
        ["Todas", "Positivas", "Negativas"]
    )

# ============================================================
# 3. APLICAR FILTROS
# ============================================================

if isinstance(periodo, (tuple, list)) and len(periodo) == 2:

    fecha_inicio, fecha_fin = periodo

    if fecha_inicio > fecha_fin:
        st.error("El período seleccionado no es válido.")
        st.stop()

    filtradas = resenas[
        (resenas["fecha_analisis"].dt.date >= fecha_inicio) &
        (resenas["fecha_analisis"].dt.date <= fecha_fin)
    ].copy()

else:
    filtradas = resenas[
        resenas["fecha_analisis"].dt.date == periodo
    ].copy()

if idioma != "Todos":
    filtradas = filtradas[
        filtradas["language_code"] == idioma
    ]

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

if filtradas.empty:
    st.warning("No existen registros para los filtros seleccionados.")
    st.stop()

# ============================================================
# 4. INDICADORES
# ============================================================

st.divider()

st.subheader("Indicadores del período seleccionado")

total_resenas = len(filtradas)

usuarios = filtradas["steamid"].nunique()
cantidad_juegos = filtradas["name"].nunique()

valoraciones = filtradas["voted_up"].dropna()

positivas = int((valoraciones == True).sum())
negativas = int((valoraciones == False).sum())

total_valoraciones = positivas + negativas

porcentaje_positivo = (
    positivas / total_valoraciones * 100
    if total_valoraciones else 0
)

porcentaje_negativo = (
    negativas / total_valoraciones * 100
    if total_valoraciones else 0
)

col1, col2, col3 = st.columns(3)

col1.metric("Reseñas", f"{total_resenas:,}")
col2.metric("Usuarios", f"{usuarios:,}")
col3.metric("Juegos", f"{cantidad_juegos:,}")

col1, col2 = st.columns(2)

col1.metric(
    "Aceptación positiva",
    f"{porcentaje_positivo:.2f}%",
    f"{positivas:,} reseñas"
)

col2.metric(
    "Aceptación negativa",
    f"{porcentaje_negativo:.2f}%",
    f"{negativas:,} reseñas"
)

st.caption(
    "Las valoraciones se calculan sobre las reseñas con "
    "recomendación válida."
)

# ============================================================
# 5. DISTRIBUCION DE VALORACIONES
# ============================================================

st.divider()

st.subheader("Distribución de recomendaciones")

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        grafico_sentimiento(filtradas),
        use_container_width=True
    )

with col2:
    distribucion = pd.DataFrame({
        "Tipo": ["Positivas", "Negativas"],
        "Cantidad": [positivas, negativas]
    })

    st.dataframe(
        distribucion,
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# 6. EVOLUCION MENSUAL
# ============================================================

st.divider()

st.subheader("Evolución mensual de reseñas")

actividad = (
    filtradas
    .assign(
        year=filtradas["fecha_analisis"].dt.year,
        month=filtradas["fecha_analisis"].dt.month,
        periodo=filtradas["fecha_analisis"].dt.strftime("%Y-%m")
    )
    .groupby(
        ["year", "month", "periodo"],
        as_index=False
    )
    .size()
    .rename(columns={"size": "cantidad_resenas"})
)

if not actividad.empty:

    st.plotly_chart(
        grafico_actividad_mensual(actividad),
        use_container_width=True
    )

    pico = actividad.loc[
        actividad["cantidad_resenas"].idxmax()
    ]

    st.caption(
        f"Mayor actividad: {pico['periodo']} "
        f"({pico['cantidad_resenas']:,} reseñas)."
    )

# ============================================================
# 7. RANKING DE JUEGOS
# ============================================================

st.divider()

st.subheader("Ranking de videojuegos")

ranking = (
    filtradas
    .groupby("name", as_index=False)
    .agg(
        cantidad_resenas=("recommendationid", "count"),
        positivas=("voted_up", lambda x: (x == True).sum()),
        negativas=("voted_up", lambda x: (x == False).sum()),
        total_valoraciones=("voted_up", "count")
    )
)

ranking["porcentaje_positivo"] = (
    ranking["positivas"]
    .div(ranking["total_valoraciones"].where(
        ranking["total_valoraciones"] > 0
    ))
    .mul(100)
)

ranking["porcentaje_negativo"] = (
    ranking["negativas"]
    .div(ranking["total_valoraciones"].where(
        ranking["total_valoraciones"] > 0
    ))
    .mul(100)
)

limite = st.slider(
    "Cantidad de juegos",
    min_value=5,
    max_value=30,
    value=10
)

ranking = ranking.sort_values(
    "cantidad_resenas",
    ascending=False
)

st.plotly_chart(
    grafico_ranking_juegos(ranking, limite),
    use_container_width=True
)

st.dataframe(
    ranking.head(limite),
    use_container_width=True,
    hide_index=True
)

# ============================================================
# 8. DIAGNOSTICO EMPRESARIAL
# ============================================================

st.divider()

st.header("Diagnóstico empresarial")

if porcentaje_negativo >= 30:

    st.error(
        f"""
        Riesgo elevado: el {porcentaje_negativo:.2f}% de las
        valoraciones son negativas.

        Acción: investigar problemas recurrentes y priorizar
        mejoras que puedan aumentar la satisfacción.
        """
    )

elif porcentaje_negativo >= 20:

    st.warning(
        f"""
        Señal de atención: el {porcentaje_negativo:.2f}% de las
        valoraciones son negativas.

        Acción: analizar las causas de insatisfacción y evaluar
        mejoras en rendimiento, contenido y experiencia.
        """
    )

elif porcentaje_positivo >= 80:

    st.success(
        f"""
        Señal favorable: el {porcentaje_positivo:.2f}% de las
        valoraciones son positivas.

        Acción: identificar los atributos mejor valorados y
        estudiar estrategias de comunidad y fidelización.
        """
    )

else:

    st.info(
        "Aceptación intermedia. Conviene analizar las causas "
        "de las valoraciones positivas y negativas."
    )

st.caption(
    "Los umbrales son criterios exploratorios, no estándares universales."
)

# ============================================================
# 9. OPORTUNIDADES POR JUEGO
# ============================================================

st.divider()

st.subheader("Oportunidades detectadas")

if not ranking.empty:

    col1, col2 = st.columns(2)

    with col1:

        mayor_volumen = ranking.iloc[0]

        st.markdown("**Mayor volumen de reseñas**")

        st.write(mayor_volumen["name"])

        st.metric(
            "Reseñas",
            f"{mayor_volumen['cantidad_resenas']:,}"
        )

        st.caption(
            "Investigar los factores que generan interés y "
            "participación para identificar oportunidades de posicionamiento."
        )

    with col2:

        muestra = ranking[
            ranking["total_valoraciones"] >= 30
        ].dropna(
            subset=["porcentaje_positivo"]
        )

        if not muestra.empty:

            mejor = muestra.loc[
                muestra["porcentaje_positivo"].idxmax()
            ]

            st.markdown("**Mayor aceptación con muestra suficiente**")

            st.write(mejor["name"])

            st.metric(
                "Positividad",
                f"{mejor['porcentaje_positivo']:.2f}%"
            )

            st.caption(
                "Resultado basado en al menos 30 valoraciones válidas."
            )

        else:

            st.info(
                "No hay juegos con una muestra mínima de 30 valoraciones."
            )

# ============================================================
# 10. RECOMENDACIONES POR PUBLICO
# ============================================================

st.divider()

st.subheader("Recomendaciones empresariales")

tab1, tab2, tab3 = st.tabs([
    "Desarrolladores",
    "Publishers",
    "Inversores"
])

with tab1:

    st.markdown(
        """
        - Priorizar problemas recurrentes en las reseñas negativas.
        - Identificar características asociadas con la aceptación.
        - Medir cambios de percepción después de actualizaciones.
        - Evaluar oportunidades de mejora de experiencia.
        """
    )

with tab2:

    st.markdown(
        """
        - Identificar productos con interés y buena aceptación.
        - Investigar riesgos reputacionales antes de ampliar campañas.
        - Comparar videojuegos y segmentos de mercado.
        - Contrastar participación con conversión y ventas.
        """
    )

with tab3:

    st.markdown(
        """
        - Utilizar las reseñas como señal complementaria de demanda.
        - Investigar tendencias de participación y aceptación.
        - Contrastar indicadores con ingresos, costos y ventas.
        - Evaluar la sostenibilidad comercial de cada producto.
        """
    )

st.warning(
    """
    Las reseñas no representan directamente ventas, ingresos,
    beneficios ni rentabilidad. Para estimarlos se necesitan
    datos económicos y comerciales adicionales.
    """
)

# ============================================================
# 11. RESUMEN
# ============================================================

st.divider()

st.subheader("Resumen del análisis")

col1, col2, col3 = st.columns(3)

col1.metric("Reseñas analizadas", f"{total_resenas:,}")
col2.metric("Aceptación positiva", f"{porcentaje_positivo:.2f}%")
col3.metric("Juegos analizados", f"{cantidad_juegos:,}")

st.caption(
    "Resultados dinámicos según los filtros seleccionados."
)
