def predecir_sentimiento(modelo, texto):

    if not isinstance(texto, str):
        raise TypeError("La reseña debe ser un texto.")

    texto = texto.strip()

    if not texto:
        raise ValueError("La reseña no puede estar vacía.")

    prediccion = modelo.predict([texto])[0]

    resultado = {
        1: "Positiva",
        0: "Negativa",
        True: "Positiva",
        False: "Negativa"
    }

    sentimiento = resultado.get(prediccion, str(prediccion))

    margen = None

    if hasattr(modelo, "decision_function"):
        margen = float(modelo.decision_function([texto])[0])

    return {
        "prediccion": prediccion,
        "sentimiento": sentimiento,
        "margen_decision": margen
    }
