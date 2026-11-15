import plotly.express as px


def grafico_sentimiento(df):
    datos = (
        df.dropna(subset=["voted_up"])["voted_up"]
        .value_counts()
        .rename_axis("sentimiento")
        .reset_index(name="cantidad")
    )

    datos["sentimiento"] = datos["sentimiento"].map({
        True: "Positiva",
        False: "Negativa"
    })

    return px.pie(
        datos,
        names="sentimiento",
        values="cantidad",
        hole=0.45,
        title="Distribución de reseñas"
    )


def grafico_actividad_mensual(df):
    datos = df.sort_values(["year", "month"])

    return px.line(
        datos,
        x="periodo",
        y="cantidad_resenas",
        markers=True,
        title="Actividad mensual de reseñas",
        labels={
            "periodo": "Período",
            "cantidad_resenas": "Cantidad de reseñas"
        }
    )


def grafico_cohortes(df):
    datos = df.sort_values("account_created_year")

    return px.bar(
        datos,
        x="account_created_year",
        y="porcentaje_positivo",
        text_auto=".1f",
        title="Porcentaje de reseñas positivas por cohorte",
        labels={
            "account_created_year": "Año de creación de cuenta",
            "porcentaje_positivo": "Reseñas positivas (%)"
        }
    )


def grafico_ranking_juegos(df, limite=10):
    datos = df.nlargest(limite, "cantidad_resenas")

    return px.bar(
        datos.sort_values("cantidad_resenas"),
        x="cantidad_resenas",
        y="name",
        orientation="h",
        title=f"Top {limite} juegos por cantidad de reseñas",
        labels={
            "cantidad_resenas": "Cantidad de reseñas",
            "name": "Juego"
        }
    )
