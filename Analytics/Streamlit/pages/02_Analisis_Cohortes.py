import streamlit as st
import pandas as pd
import plotly.express as px

from utils import mostrar_navegacion
from utils.data_loader import cargar_datasets
from utils.visualizaciones import grafico_cohortes

st.set_page_config(
    page_title="Análisis de cohortes",
    page_icon="👥",
    layout="wide"
)

mostrar_navegacion()

# ============================================================
# 1. CARGA Y VALIDACION
# ============================================================

datos = cargar_datasets()

cohortes = datos["resenas_cohortes"].copy()
resumen = datos["resumen_cohortes"].copy()

st.title("👥 Análisis de cohortes")

st.markdown(
    """
    Comparación del comportamiento de los usuarios según
    el año de creación de su cuenta de Steam.

    Buscamos identificar diferencias en participación,
    aceptación y oportunidades de segmentación comercial.
    """
)

ANIOS_COHORTE = list(range(2020, 2026))

columnas_requeridas = [
    "account_created_year",
    "cantidad_resenas",
    "usuarios",
    "juegos",
    "positivas",
    "negativas",
    "porcentaje_positivo",
    "porcentaje_negativo"
]

faltantes = [
    c for c in columnas_requeridas
    if c not in resumen.columns
]

if faltantes:
    st.error(
        "Faltan columnas del resumen: " + ", ".join(faltantes)
    )
    st.stop()

if "account_created_year" not in cohortes.columns:
    st.error("Falta account_created_year en las reseñas.")
    st.stop()

resumen = resumen[
    resumen["account_created_year"].isin(ANIOS_COHORTE)
].copy()

cohortes = cohortes[
    cohortes["account_created_year"].isin(ANIOS_COHORTE)
].copy()

if resumen.empty or cohortes.empty:
    st.warning("No hay datos disponibles para las cohortes 2020–2025.")
    st.stop()

for columna in columnas_requeridas[1:]:
    resumen[columna] = pd.to_numeric(
        resumen[columna],
        errors="coerce"
    ).fillna(0)

resumen["account_created_year"] = (
    resumen["account_created_year"].astype(int)
)

resumen = resumen.sort_values(
    "account_created_year"
).reset_index(drop=True)

# ============================================================
# 2. INDICADORES GENERALES
# ============================================================

st.info(
    "Análisis principal limitado a las seis cohortes 2020–2025."
)

total_resenas = int(resumen["cantidad_resenas"].sum())
total_usuarios = int(resumen["usuarios"].sum())
total_positivas = int(resumen["positivas"].sum())
total_negativas = int(resumen["negativas"].sum())

total_valoraciones = total_positivas + total_negativas

porcentaje_positivo = (
    total_positivas / total_valoraciones * 100
    if total_valoraciones else 0
)

porcentaje_negativo = (
    total_negativas / total_valoraciones * 100
    if total_valoraciones else 0
)

promedio_usuario = (
    total_resenas / total_usuarios
    if total_usuarios else 0
)

st.subheader("Indicadores generales")

col1, col2, col3 = st.columns(3)

col1.metric("Reseñas", f"{total_resenas:,}")
col2.metric("Usuarios", f"{total_usuarios:,}")
col3.metric("Juegos por cohorte", f"{int(resumen['juegos'].sum()):,}")

col1, col2, col3 = st.columns(3)

col1.metric("Positividad", f"{porcentaje_positivo:.2f}%")
col2.metric("Negatividad", f"{porcentaje_negativo:.2f}%")
col3.metric("Reseñas por usuario", f"{promedio_usuario:.2f}")

st.caption(
    "Los usuarios se contabilizan por cohorte. No se suman como "
    "usuarios únicos globales si un usuario puede aparecer "
    "en más de una cohorte."
)

# ============================================================
# 3. TABLA COMPARATIVA
# ============================================================

st.divider()

st.subheader("Indicadores por cohorte")

tabla = resumen.copy()

tabla["resenas_por_usuario"] = (
    tabla["cantidad_resenas"]
    .div(tabla["usuarios"].where(tabla["usuarios"] > 0))
)

tabla_presentacion = tabla.rename(
    columns={
        "account_created_year": "Cohorte",
        "cantidad_resenas": "Reseñas",
        "usuarios": "Usuarios",
        "juegos": "Juegos",
        "positivas": "Positivas",
        "negativas": "Negativas",
        "porcentaje_positivo": "% positivo",
        "porcentaje_negativo": "% negativo",
        "resenas_por_usuario": "Reseñas por usuario"
    }
)

st.dataframe(
    tabla_presentacion.round(2),
    use_container_width=True,
    hide_index=True
)

# ============================================================
# 4. PARTICIPACION POR COHORTE
# ============================================================

st.divider()

st.subheader("Participación de las cohortes")

fig_participacion = px.bar(
    resumen,
    x="account_created_year",
    y="cantidad_resenas",
    text="cantidad_resenas",
    labels={
        "account_created_year": "Año de creación de cuenta",
        "cantidad_resenas": "Reseñas"
    },
    title="Volumen de reseñas por cohorte"
)

fig_participacion.update_traces(
    textposition="outside"
)

fig_participacion.update_layout(
    xaxis=dict(tickmode="linear", dtick=1),
    showlegend=False
)

st.plotly_chart(
    fig_participacion,
    use_container_width=True
)

# ============================================================
# 5. ACTIVIDAD POR USUARIO
# ============================================================

st.divider()

st.subheader("Actividad promedio por usuario")

fig_actividad = px.bar(
    tabla,
    x="account_created_year",
    y="resenas_por_usuario",
    text="resenas_por_usuario",
    labels={
        "account_created_year": "Cohorte",
        "resenas_por_usuario": "Reseñas por usuario"
    },
    title="Promedio de reseñas por usuario"
)

fig_actividad.update_traces(
    texttemplate="%{text:.2f}",
    textposition="outside"
)

fig_actividad.update_layout(
    xaxis=dict(tickmode="linear", dtick=1),
    showlegend=False
)

st.plotly_chart(
    fig_actividad,
    use_container_width=True
)

# ============================================================
# 6. ACEPTACION POR COHORTE
# ============================================================

st.divider()

st.subheader("Evolución de la aceptación")

st.plotly_chart(
    grafico_cohortes(resumen),
    use_container_width=True
)

fig_valoraciones = px.line(
    resumen,
    x="account_created_year",
    y=["porcentaje_positivo", "porcentaje_negativo"],
    markers=True,
    labels={
        "account_created_year": "Cohorte",
        "value": "Porcentaje",
        "variable": "Valoración"
    },
    title="Porcentaje de valoraciones por cohorte"
)

fig_valoraciones.update_layout(
    xaxis=dict(tickmode="linear", dtick=1),
    yaxis_title="Porcentaje (%)"
)

st.plotly_chart(
    fig_valoraciones,
    use_container_width=True
)

primera = resumen.iloc[0]
ultima = resumen.iloc[-1]

diferencia = (
    ultima["porcentaje_positivo"]
    - primera["porcentaje_positivo"]
)

st.metric(
    "Diferencia de positividad entre primera y última cohorte",
    f"{diferencia:+.2f} puntos porcentuales"
)

st.caption(
    "La diferencia es descriptiva y no implica causalidad."
)

# ============================================================
# 7. COMPARACION ENTRE DOS COHORTES
# ============================================================

st.divider()

st.subheader("Comparación detallada")

anios = sorted(
    resumen["account_created_year"].unique().tolist()
)

col1, col2 = st.columns(2)

with col1:
    cohorte_a = st.selectbox(
        "Primera cohorte",
        anios,
        index=0
    )

with col2:
    cohorte_b = st.selectbox(
        "Segunda cohorte",
        anios,
        index=len(anios) - 1,
        key="cohorte_comparacion_b"
    )

fila_a = resumen[
    resumen["account_created_year"] == cohorte_a
].iloc[0]

fila_b = resumen[
    resumen["account_created_year"] == cohorte_b
].iloc[0]

comparacion = []

for nombre, columna in [
    ("Reseñas", "cantidad_resenas"),
    ("Usuarios", "usuarios"),
    ("Juegos", "juegos"),
    ("Positivas", "positivas"),
    ("Negativas", "negativas"),
    ("% positivo", "porcentaje_positivo"),
    ("% negativo", "porcentaje_negativo")
]:

    valor_a = fila_a[columna]
    valor_b = fila_b[columna]

    comparacion.append({
        "Indicador": nombre,
        str(cohorte_a): round(valor_a, 2),
        str(cohorte_b): round(valor_b, 2),
        "Diferencia": round(valor_b - valor_a, 2)
    })

st.dataframe(
    pd.DataFrame(comparacion),
    use_container_width=True,
    hide_index=True
)

# ============================================================
# 8. EXPLORACION DE UNA COHORTE
# ============================================================

st.divider()

st.subheader("Exploración de usuarios y reseñas")

anio = st.selectbox(
    "Seleccionar cohorte",
    anios,
    key="cohorte_exploracion"
)

filtradas = cohortes[
    cohortes["account_created_year"] == anio
].copy()

if filtradas.empty:

    st.warning("No hay reseñas para la cohorte seleccionada.")

else:

    positivas = int(
        filtradas["voted_up"].eq(True).sum()
    )

    negativas = int(
        filtradas["voted_up"].eq(False).sum()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Reseñas", f"{len(filtradas):,}")
    col2.metric("Positivas", f"{positivas:,}")
    col3.metric("Negativas", f"{negativas:,}")

    distribucion = pd.DataFrame({
        "Tipo": ["Positivas", "Negativas"],
        "Cantidad": [positivas, negativas]
    })

    fig_distribucion = px.pie(
        distribucion,
        names="Tipo",
        values="Cantidad",
        hole=0.45
    )

    st.plotly_chart(
        fig_distribucion,
        use_container_width=True
    )

    st.markdown("**Juegos con mayor participación**")

    ranking = (
        filtradas
        .groupby("name", as_index=False)
        .agg(
            cantidad_resenas=("recommendationid", "count"),
            positivas=("voted_up", lambda x: (x == True).sum()),
            negativas=("voted_up", lambda x: (x == False).sum())
        )
    )

    total = ranking["positivas"] + ranking["negativas"]

    ranking["porcentaje_positivo"] = (
        ranking["positivas"]
        .div(total.where(total > 0))
        .mul(100)
    )

    ranking = ranking.sort_values(
        "cantidad_resenas",
        ascending=False
    )

    st.dataframe(
        ranking.head(10),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("**Muestra de reseñas**")

    columnas = [
        c for c in [
            "account_created_year",
            "name",
            "voted_up",
            "review"
        ]
        if c in filtradas.columns
    ]

    st.dataframe(
        filtradas[columnas].head(100),
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# 9. DIAGNOSTICO EMPRESARIAL
# ============================================================

st.divider()

st.header("Diagnóstico empresarial")

mayor_volumen = resumen.loc[
    resumen["cantidad_resenas"].idxmax()
]

mayor_aceptacion = resumen.loc[
    resumen["porcentaje_positivo"].idxmax()
]

menor_aceptacion = resumen.loc[
    resumen["porcentaje_positivo"].idxmin()
]

mayor_actividad = tabla.loc[
    tabla["resenas_por_usuario"].idxmax()
]

col1, col2 = st.columns(2)

with col1:

    st.markdown("**Mayor participación**")

    st.metric(
        f"Cohorte {int(mayor_volumen['account_created_year'])}",
        f"{int(mayor_volumen['cantidad_resenas']):,} reseñas"
    )

with col2:

    st.markdown("**Mayor aceptación**")

    st.metric(
        f"Cohorte {int(mayor_aceptacion['account_created_year'])}",
        f"{mayor_aceptacion['porcentaje_positivo']:.2f}%"
    )

st.write(
    f"La menor aceptación corresponde a la cohorte "
    f"{int(menor_aceptacion['account_created_year'])}, con "
    f"{menor_aceptacion['porcentaje_positivo']:.2f}%."
)

st.write(
    f"La mayor actividad promedio corresponde a la cohorte "
    f"{int(mayor_actividad['account_created_year'])}, con "
    f"{mayor_actividad['resenas_por_usuario']:.2f} reseñas por usuario."
)

# ============================================================
# 10. RECOMENDACIONES ESTRATEGICAS
# ============================================================

st.divider()

st.subheader("Recomendaciones estratégicas")

tab1, tab2, tab3 = st.tabs([
    "Desarrolladores",
    "Publishers",
    "Inversores"
])

with tab1:

    st.markdown(
        """
        - Investigar diferencias de aceptación entre cohortes.
        - Analizar problemas recurrentes por segmento.
        - Identificar géneros y atributos con mayor participación.
        - Evaluar mejoras de producto según las necesidades detectadas.
        """
    )

with tab2:

    st.markdown(
        """
        - Segmentar campañas según patrones de participación.
        - Identificar cohortes con mayor actividad observada.
        - Evaluar estrategias de comunidad y fidelización.
        - Contrastar el interés con datos de conversión y ventas.
        """
    )

with tab3:

    st.markdown(
        """
        - Utilizar la aceptación como señal complementaria de demanda.
        - Investigar la evolución de participación por generación.
        - Contrastar la información con indicadores financieros.
        - Evaluar riesgos de producto y oportunidades de mercado.
        """
    )

st.warning(
    """
    Las cohortes no representan directamente ventas, ingresos,
    retención ni beneficios. Para evaluar rentabilidad se necesitan
    datos comerciales, financieros y temporales adicionales.
    """
)

# ============================================================
# 11. RESUMEN EJECUTIVO
# ============================================================

st.divider()

st.header("Resumen ejecutivo")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Mayor volumen",
    str(int(mayor_volumen["account_created_year"]))
)

col2.metric(
    "Mayor aceptación",
    str(int(mayor_aceptacion["account_created_year"]))
)

col3.metric(
    "Mayor actividad",
    str(int(mayor_actividad["account_created_year"]))
)

st.markdown(
    f"""
    El análisis principal comprende **{total_resenas:,} reseñas**
    de las cohortes 2020–2025.

    La aceptación positiva general es del
    **{porcentaje_positivo:.2f}%**.

    La cohorte con mayor volumen es
    **{int(mayor_volumen['account_created_year'])}**,
    mientras que la mayor aceptación corresponde a
    **{int(mayor_aceptacion['account_created_year'])}**.

    Estos resultados permiten orientar investigaciones
    comerciales y decisiones de producto.
    """
)

st.caption(
    "Steam Analytics | Cohortes principales 2020–2025."
)
