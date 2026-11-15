import streamlit as st

from utils.data_loader import cargar_datasets, cargar_modelo


# ------------------------------------------------------------
# CONFIGURACION
# ------------------------------------------------------------

st.set_page_config(
    page_title="Steam Analytics",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ------------------------------------------------------------
# CARGA DE RECURSOS
# ------------------------------------------------------------

try:
    datos = cargar_datasets()
    modelo = cargar_modelo()

except Exception as error:
    st.error(f"Error al cargar los recursos: {error}")
    st.stop()


# ------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------

with st.sidebar:

    st.title("🎮 Steam Analytics")

    st.caption(
        "Business Intelligence | Gaming Market Analytics"
    )

    st.divider()

    st.subheader("PLATAFORMA ANALITICA")

    st.page_link(
        "app.py",
        label="Inicio",
        icon="🏠"
    )

    st.page_link(
        "pages/01_Analisis_General.py",
        label="Análisis general",
        icon="📊"
    )

    st.page_link(
        "pages/02_Analisis_Cohortes.py",
        label="Cohortes y usuarios",
        icon="👥"
    )

    st.page_link(
        "pages/03_Exploracion_Juegos.py",
        label="Exploración de juegos",
        icon="🎮"
    )

    st.page_link(
        "pages/04_Analisis_Sentimiento.py",
        label="Análisis de sentimiento",
        icon="💬"
    )

    st.divider()

    st.subheader("INFORMACION DEL PROYECTO")

    st.caption(
        "Fuentes de datos, metodología y "
        "documentación del modelo disponibles "
        "en la sección informativa de Inicio."
    ) 

    st.divider()

    st.caption(
        "Steam Analytics | Data Science & Machine Learning"
    )



# ------------------------------------------------------------
# PORTADA
# ------------------------------------------------------------

st.title("Steam Analytics")

st.subheader(
    "Análisis de reseñas, cohortes de usuarios y sentimiento"
)

st.markdown(
    """
    Plataforma interactiva de análisis de datos de Steam.

    Integra información de reseñas, usuarios, juegos y novedades
    para explorar patrones de comportamiento, comparar cohortes
    y analizar opiniones mediante NLP y Machine Learning.
    """
)

st.divider()


# ------------------------------------------------------------
# INDICADORES GENERALES
# ------------------------------------------------------------

st.header("Indicadores generales")

kpis = datos["kpis_generales"]

valores = dict(zip(kpis["indicador"], kpis["valor"]))

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total de reseñas",
        f"{valores['Total de reseñas']:,.0f}"
    )

with col2:
    st.metric(
        "Usuarios con reseñas",
        f"{valores['Usuarios con reseñas']:,.0f}"
    )

with col3:
    st.metric(
        "Juegos con reseñas",
        f"{valores['Juegos con reseñas']:,.0f}"
    )

with col4:
    st.metric(
        "Porcentaje positivo",
        f"{valores['Porcentaje positivo']:.2f}%"
    )

col5, col6 = st.columns(2)

with col5:
    st.metric(
        "Reseñas positivas",
        f"{valores['Reseñas positivas']:,.0f}"
    )

with col6:
    st.metric(
        "Reseñas negativas",
        f"{valores['Reseñas negativas']:,.0f}"
    )


# ------------------------------------------------------------
# INFORMACION DEL PROYECTO
# ------------------------------------------------------------

st.divider()

st.header("Sobre Steam Analytics")

st.markdown(
    """
    **Steam Analytics** es una plataforma de Business Intelligence
    que integra Ciencia de Datos, análisis estadístico y Machine
    Learning para transformar información de Steam en conocimiento
    estratégico para la industria de los videojuegos.
    """
)

st.subheader("Objetivo de la plataforma")

st.write(
    """
    Identificar patrones de comportamiento de usuarios, preferencias
    de videojuegos, evolución de las valoraciones y tendencias de
    sentimiento para generar recomendaciones empresariales.

    El propósito es ayudar a desarrolladores, publishers e inversores
    a detectar oportunidades comerciales, anticipar riesgos y
    respaldar decisiones orientadas a mejorar el rendimiento
    de sus productos y estrategias de mercado.
    """
)

st.divider()

# ------------------------------------------------------------
# PUBLICO OBJETIVO
# ------------------------------------------------------------

st.subheader("Público objetivo")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🎮 Desarrolladores")
    st.write(
        """
        - Identificar problemas recurrentes.
        - Analizar la satisfacción de jugadores.
        - Detectar oportunidades de mejora.
        - Priorizar futuras actualizaciones.
        """
    )

with col2:
    st.markdown("### 🏢 Publishers")
    st.write(
        """
        - Evaluar el comportamiento del mercado.
        - Identificar preferencias de usuarios.
        - Comparar el rendimiento de videojuegos.
        - Detectar oportunidades de posicionamiento.
        """
    )

with col3:
    st.markdown("### 📈 Inversores")
    st.write(
        """
        - Identificar tendencias de mercado.
        - Analizar indicadores de desempeño.
        - Evaluar señales de aceptación.
        - Explorar oportunidades de inversión.
        """
    )

st.divider()

# ------------------------------------------------------------
# CAPACIDADES ANALITICAS
# ------------------------------------------------------------

st.subheader("Capacidades analíticas")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Análisis exploratorio y estadístico")
    st.write(
        """
        - Indicadores generales de actividad.
        - Análisis de cohortes de usuarios.
        - Distribución de recomendaciones.
        - Evolución temporal de reseñas y novedades.
        - Comparación del rendimiento entre juegos.
        """
    )

with col2:
    st.markdown("#### Inteligencia artificial y Machine Learning")
    st.write(
        """
        - Procesamiento de lenguaje natural (NLP).
        - Vectorización TF-IDF.
        - Clasificación de sentimientos.
        - Modelo Linear Support Vector Machine.
        - Evaluación y análisis de errores predictivos.
        """
    )

st.divider()

# ------------------------------------------------------------
# FUENTES DE DATOS Y METODOLOGIA
# ------------------------------------------------------------

st.subheader("Fuentes de datos y metodología")

st.write(
    """
    La plataforma utiliza información obtenida de Steam mediante
    procesos de extracción y transformación de datos organizados
    bajo una arquitectura Medallion.
    """
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🥉 Bronze")
    st.caption("Extracción")
    st.write(
        "Datos originales de juegos, usuarios, reseñas y novedades."
    )

with col2:
    st.markdown("### 🥈 Silver")
    st.caption("Transformación")
    st.write(
        "Limpieza, normalización, consolidación y validación."
    )

with col3:
    st.markdown("### 🥇 Gold")
    st.caption("Análisis")
    st.write(
        "Dimensiones, tablas de hechos y agregaciones analíticas."
    )

st.info(
    """
    **Alcance temporal principal:** cohortes de usuarios 2020–2025.
    Los datos de otros períodos pueden conservarse como contexto
    exploratorio, pero no forman parte de las comparaciones
    principales entre cohortes.
    """
)

st.divider()

# ------------------------------------------------------------
# MODELO PREDICTIVO
# ------------------------------------------------------------

st.subheader("Modelo de clasificación de sentimientos")

st.write(
    """
    Steam Analytics incorpora un modelo de Machine Learning basado
    en TF-IDF y Linear Support Vector Machine (Linear SVM), diseñado
    para clasificar automáticamente el contenido textual de las
    reseñas según su orientación positiva o negativa.
    """
)

st.markdown(
    """
    **Aplicaciones empresariales:**
    - Identificar temas asociados con experiencias positivas y negativas.
    - Detectar problemas recurrentes mencionados por los jugadores.
    - Analizar señales de aceptación de productos.
    - Respaldar decisiones de actualización y mejora.
    """
)

st.divider()

# ------------------------------------------------------------
# INTELIGENCIA EMPRESARIAL Y RENTABILIDAD
# ------------------------------------------------------------

st.subheader("De los datos a las decisiones empresariales")

st.write(
    """
    La plataforma busca transformar los resultados analíticos
    en recomendaciones accionables. Cada hallazgo relevante debe
    vincularse con una posible oportunidad o riesgo empresarial.
    """
)

st.markdown(
    """
    **Estructura de las recomendaciones:**

    1. **Hallazgo:** qué muestran los datos.
    2. **Diagnóstico:** qué puede explicar el comportamiento observado.
    3. **Oportunidad o riesgo:** qué implica para el negocio.
    4. **Acción recomendada:** qué decisión se puede evaluar.
    5. **Impacto económico potencial:** cómo podría contribuir
       a mejorar ingresos, reducir costos o fortalecer la retención.
    6. **KPI de seguimiento:** cómo evaluar los resultados de la acción.
    """
)

st.warning(
    """
    Las oportunidades de rentabilidad son estimaciones potenciales
    basadas en evidencia analítica. No representan beneficios
    económicos garantizados ni relaciones causales demostradas.
    """
)

st.divider()

# ------------------------------------------------------------
# IDENTIDAD DEL PROYECTO
# ------------------------------------------------------------

st.caption(
    "Steam Analytics | Business Intelligence | "
    "Data Science | NLP | Machine Learning"
)
