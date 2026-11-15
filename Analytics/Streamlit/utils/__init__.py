import streamlit as st


def mostrar_navegacion():

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
            "Fuentes de datos, metodología y documentación "
            "del modelo disponibles en Inicio."
        )

        st.divider()

        st.caption(
            "Steam Analytics | Data Science & Machine Learning"
        )
