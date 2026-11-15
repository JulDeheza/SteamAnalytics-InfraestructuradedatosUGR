import streamlit as st
import pandas as pd
import plotly.express as px

from utils import mostrar_navegacion
from utils.data_loader import cargar_datasets
from utils.visualizaciones import grafico_ranking_juegos

st.set_page_config(
    page_title="Exploración de juegos",
    page_icon="🎮",
    layout="wide"
)

mostrar_navegacion()

# ============================================================
# 1. CARGA DE DATOS
# ============================================================

datos = cargar_datasets()

ranking_base = datos["ranking_juegos"].copy()
resenas = datos["resenas_dashboard"].copy()

resenas["fecha_analisis"] = pd.to_datetime(
    resenas["timestamp_created_parsed"],
    errors="coerce",
    utc=True
)

st.title("🎮 Exploración de videojuegos")

st.markdown(
    """
    Evaluación individual y comparativa de videojuegos.

    Identificamos oportunidades de posicionamiento, aceptación,
    participación y posibles problemas de producto.
    """
)

if ranking_base.empty or resenas.empty:
    st.warning("No hay información suficiente para explorar videojuegos.")
    st.stop()

# ============================================================
# 2. FILTROS DE EXPLORACION
# ============================================================

st.divider()

st.subheader("Filtros")

juegos = sorted(
    ranking_base["name"].dropna().unique().tolist()
)

busqueda = st.text_input(
    "Buscar videojuego",
    placeholder="Ingresar nombre del videojuego..."
)

if busqueda.strip():
    juegos_filtrados = [
        nombre for nombre in juegos
        if busqueda.lower() in nombre.lower()
    ]
else:
    juegos_filtrados = juegos

if not juegos_filtrados:
    st.warning("No se encontraron videojuegos con ese nombre.")
    st.stop()

seleccion = st.selectbox(
    "Seleccionar videojuego",
    juegos_filtrados
)

# ============================================================
# 3. INDICADORES DEL JUEGO
# ============================================================

detalle = resenas[
    resenas["name"] == seleccion
].copy()

if detalle.empty:
    st.warning("No hay reseñas disponibles para este videojuego.")
    st.stop()

total_resenas = len(detalle)

valoraciones = detalle["voted_up"].dropna()

positivas = int((valoraciones == True).sum())
negativas = int((valoraciones == False).sum())

total_valoraciones = len(valoraciones)

porcentaje_positivo = (
    positivas / total_valoraciones * 100
    if total_valoraciones else 0
)

porcentaje_negativo = (
    negativas / total_valoraciones * 100
    if total_valoraciones else 0
)

usuarios = detalle["steamid"].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Reseñas", f"{total_resenas:,}")
col2.metric("Usuarios", f"{usuarios:,}")
col3.metric("Positivas", f"{porcentaje_positivo:.2f}%")
col4.metric("Negativas", f"{porcentaje_negativo:.2f}%")

# ============================================================
# 4. DISTRIBUCION DE VALORACIONES
# ============================================================

st.divider()

st.subheader("Aceptación del videojuego")

col1, col2 = st.columns(2)

with col1:

    distribucion = pd.DataFrame({
        "Tipo": ["Positivas", "Negativas"],
        "Cantidad": [positivas, negativas]
    })

    fig = px.pie(
        distribucion,
        names="Tipo",
        values="Cantidad",
        hole=0.45,
        title="Distribución de recomendaciones"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with col2:

    st.metric(
        "Total de valoraciones válidas",
        f"{total_valoraciones:,}"
    )

    st.metric(
        "Usuarios que reseñaron",
        f"{usuarios:,}"
    )

    st.metric(
        "Promedio de reseñas por usuario",
        f"{total_resenas / usuarios:.2f}" if usuarios else "0"
    )

# ============================================================
# 5. EVOLUCION TEMPORAL
# ============================================================

st.divider()

st.subheader("Evolución temporal de reseñas")

temporal = (
    detalle.dropna(subset=["fecha_analisis"])
    .assign(
        periodo=lambda x: x["fecha_analisis"].dt.strftime("%Y-%m")
    )
    .groupby("periodo", as_index=False)
    .size()
    .rename(columns={"size": "cantidad_resenas"})
)

if not temporal.empty:

    fig_temporal = px.line(
        temporal,
        x="periodo",
        y="cantidad_resenas",
        markers=True,
        title="Evolución mensual de reseñas",
        labels={
            "periodo": "Mes",
            "cantidad_resenas": "Reseñas"
        }
    )

    st.plotly_chart(
        fig_temporal,
        use_container_width=True
    )

    pico = temporal.loc[
        temporal["cantidad_resenas"].idxmax()
    ]

    st.caption(
        f"Mes con mayor actividad: {pico['periodo']} "
        f"({pico['cantidad_resenas']:,} reseñas)."
    )

# ============================================================
# 6. PARTICIPACION POR IDIOMA
# ============================================================

st.divider()

st.subheader("Distribución por idioma")

if "language_code" in detalle.columns:

    idiomas = (
        detalle["language_code"]
        .fillna("No especificado")
        .value_counts()
        .head(10)
        .rename_axis("Idioma")
        .reset_index(name="Reseñas")
    )

    st.dataframe(
        idiomas,
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# 7. COMPARACION CON EL RESTO DE LOS JUEGOS
# ============================================================

st.divider()

st.subheader("Posicionamiento comparativo")

ranking = (
    resenas
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

ranking = ranking.sort_values(
    "cantidad_resenas",
    ascending=False
).reset_index(drop=True)

posicion = ranking[
    ranking["name"] == seleccion
].index

if len(posicion):

    posicion = int(posicion[0]) + 1

    st.metric(
        "Posición por volumen de reseñas",
        f"{posicion} / {len(ranking)}"
    )

    promedio_mercado = ranking[
        "porcentaje_positivo"
    ].mean()

    diferencia = porcentaje_positivo - promedio_mercado

    st.metric(
        "Diferencia frente al promedio de la muestra",
        f"{diferencia:+.2f} puntos porcentuales"
    )

# ============================================================
# 8. DIAGNOSTICO DEL VIDEOJUEGO
# ============================================================

st.divider()

st.header("Diagnóstico empresarial")

if total_valoraciones < 30:

    st.info(
        "Muestra reducida: se recomienda ampliar la observación "
        "antes de formular conclusiones comerciales."
    )

elif porcentaje_negativo >= 30:

    st.error(
        f"""
        Señal de riesgo: el {porcentaje_negativo:.2f}% de las
        valoraciones son negativas.

        Recomendación: investigar problemas de rendimiento,
        contenido, jugabilidad y experiencia del usuario.
        """
    )

elif porcentaje_positivo >= 80:

    st.success(
        f"""
        Señal favorable: el {porcentaje_positivo:.2f}% de las
        valoraciones son positivas.

        Recomendación: identificar los atributos mejor valorados
        y estudiar oportunidades de expansión y posicionamiento.
        """
    )

else:

    st.warning(
        "Aceptación intermedia: analizar las reseñas para "
        "detectar factores de satisfacción e insatisfacción."
    )

# ============================================================
# 9. OPORTUNIDADES DE MEJORA
# ============================================================

st.divider()

st.subheader("Recomendaciones por público")

tab1, tab2, tab3 = st.tabs([
    "Desarrolladores",
    "Publishers",
    "Inversores"
])

with tab1:

    st.markdown(
        """
        - Priorizar problemas recurrentes de las reseñas.
        - Analizar cambios en la percepción a lo largo del tiempo.
        - Investigar oportunidades de mejora de producto.
        - Medir la respuesta de la comunidad a las actualizaciones.
        """
    )

with tab2:

    st.markdown(
        """
        - Evaluar el posicionamiento frente a otros juegos.
        - Identificar mercados e idiomas con participación.
        - Contrastar el interés con conversión y ventas.
        - Investigar oportunidades de comunicación comercial.
        """
    )

with tab3:

    st.markdown(
        """
        - Considerar aceptación y participación como señales complementarias.
        - Evaluar riesgos reputacionales.
        - Contrastar resultados con ingresos y costos.
        - Analizar la evolución de la demanda con datos externos.
        """
    )

st.warning(
    """
    El volumen de reseñas no representa ventas ni ingresos.
    La aceptación tampoco demuestra rentabilidad.
    Se requieren datos económicos adicionales para evaluar
    el desempeño financiero del videojuego.
    """
)

# ============================================================
# 10. RESEÑAS DEL VIDEOJUEGO
# ============================================================

st.divider()

st.subheader("Explorar reseñas")

tipo = st.selectbox(
    "Filtrar reseñas",
    ["Todas", "Positivas", "Negativas"]
)

reseñas = detalle.copy()

if tipo == "Positivas":
    reseñas = reseñas[
        reseñas["voted_up"] == True
    ]

elif tipo == "Negativas":
    reseñas = reseñas[
        reseñas["voted_up"] == False
    ]

columnas = [
    c for c in [
        "timestamp_created_parsed",
        "language_code",
        "voted_up",
        "votes_up",
        "review"
    ]
    if c in reseñas.columns
]

st.dataframe(
    reseñas[columnas].head(100),
    use_container_width=True,
    hide_index=True
)
