# 🎮 Steam Analytics — Business Intelligence & Predictive Platform

## 📝 Descripción del Proyecto
**Steam Analytics** es una plataforma de Business Intelligence, Ciencia de Datos y Machine Learning diseñada para recopilar, procesar, analizar y modelar datos del ecosistema de Steam (reseñas de usuarios, datos de videojuegos, especificaciones de hardware y novedades de la comunidad).

El objetivo principal es transformar datos brutos en conocimiento de valor estratégico para **Desarrolladores**, **Publishers** e **Inversores**, permitiendo identificar patrones de comportamiento, niveles de aceptación, participación de mercado y oportunidades de monetización a través de una interfaz analítica moderna y ágil en **Streamlit**.

---

## 📸 Capturas de Pantalla del Dashboard (Visual Preview)

Haquí puedes visualizar la interfaz interactiva y analítica de la plataforma:

* **Pestaña 1: Inicio e Indicadores Generales**
  https://raw.githubusercontent.com/tu_usuario/tu_repositorio/main/Analytics/Streamlit/assets/screenshot_inicio.png

* **Pestaña 2: Análisis de Cohortes (2020-2025)**
  https://raw.githubusercontent.com/tu_usuario/tu_repositorio/main/Analytics/Streamlit/assets/screenshot_cohortes.png

* **Pestaña 3: Exploración de Videojuegos Individual**
  https://raw.githubusercontent.com/tu_usuario/tu_repositorio/main/Analytics/Streamlit/assets/screenshot_juegos.png

* **Pestaña 4: Clasificación del Sentimiento en Tiempo Real (NLP)**
  https://raw.githubusercontent.com/tu_usuario/tu_repositorio/main/Analytics/Streamlit/assets/screenshot_sentimiento.png

---

## 🧬 Arquitectura de Datos: Modelo Medallion
El flujo de ingeniería de datos y almacenamiento se organiza bajo la arquitectura **Medallion**, asegurando trazabilidad, calidad y consistencia desde la ingesta inicial hasta el consumo analítico:

1. ** Capa Bronze (Raw Data):**
   - Contiene la extracción directa de los datos origen en formato bruto (JSON, CSV, tablas desestructuradas) sin ningún tipo de filtrado.
2. ** Capa Silver (Clean & Enriched):**
   - Limpieza, normalización de esquemas, tratamiento robusto de nulos, desanidación de estructuras de datos complejas (como autores de reseñas), parseo de marcas de tiempo y validación sintáctica de tipos de datos.
3. ** Capa Gold (Business-Level Dimensional Model):**
   - Modelo dimensional de estrella optimizado para consultas de alta velocidad. Se compone de:
     - **Dimensiones:** `dim_usuarios`, `dim_juegos`, `dim_fecha`, `dim_idioma`, `dim_hardware`.
     - **Tablas de Hechos:** `fact_resenas`, `fact_novedades`.
     - **Agregaciones:** `agg_juego_mes` (para visualización ágil de tendencias históricas).

---

## 📁 Estructura del Módulo de Despliegue
La aplicación está estructurada de forma modular para garantizar la escalabilidad y facilitar el mantenimiento:

```directory
Analytics/Streamlit/
├── app.py                      # Punto de entrada y Portada de la aplicación
├── requirements.txt            # Dependencias del entorno de ejecución
├── README.md                   # Documentación oficial del proyecto
├── Data/                       # Datasets optimizados en formato Parquet
│   ├── resenas_dashboard.parquet
│   ├── resenas_cohortes.parquet
│   ├── kpis_generales.parquet
│   ├── resumen_cohortes.parquet
│   ├── actividad_mensual.parquet
│   └── ranking_juegos.parquet
├── models/                     # Modelo predictivo NLP entrenado y serializado
│   └── steam_linear_svm_tfidf_final.joblib
├── pages/                      # Páginas del Dashboard interactivo
│   ├── 01_Analisis_General.py  # Diagnóstico general, KPI de aceptación y volumen
│   ├── 02_Analisis_Cohortes.py # Comportamiento de usuarios (cohortes 2020-2025)
│   ├── 03_Exploracion_Juegos.py# Perfil individual de videojuegos y comparación de mercado
│   └── 04_Analisis_Sentimiento.py# Clasificación en tiempo real de nuevas opiniones escritas
└── utils/                      # Funciones auxiliares y lógica de negocio
    ├── __init__.py             # Navegación lateral compartida
    ├── data_loader.py          # Carga de recursos con sistema de caché de Streamlit
    ├── visualizaciones.py      # Definición de gráficos interactivos Plotly
    └── predicciones.py         # Lógica de inferencia predictiva con el modelo SVM
```

---

## 📊 Módulos Funcionales del Dashboard

### 1.  Inicio (Punto de Entrada - `app.py`)
Presenta los KPIs globales de la plataforma, describe la metodología de obtención de datos bajo el pipeline Medallion, introduce al público objetivo (desarrolladores, publishers e inversores) y explica la estructura de las oportunidades de rentabilidad empresarial.

### 2. 📊 Análisis General (`01_Analisis_General.py`)
Permite filtrar dinámicamente por períodos, idiomas, videojuegos específicos y tipo de recomendación. Incluye:
- Tarjetas con métricas principales (Reseñas, Usuarios, Juegos).
- Distribución interactiva de valoraciones positivas y negativas.
- Línea de tiempo de la evolución mensual de actividad.
- Gráfico de barras horizontal con el ranking de los títulos más reseñados.
- Motor diagnóstico que arroja advertencias de riesgo o felicitaciones por alta aceptación basadas en umbrales lógicos.

### 3. 👥 Cohortes y Usuarios (`02_Analisis_Cohortes.py`)
Estudio enfocado en las cohortes de creación de cuenta de usuarios del período **2020–2025**:
- Análisis del volumen de participación por cohorte.
- Promedio de reseñas redactadas por usuario para medir retención y fidelización.
- Línea de tendencia histórica de porcentajes de positividad y negatividad.
- Comparador interactivo directo cara a cara entre dos cohortes seleccionadas.
- Tabla interactiva para profundizar en opiniones detalladas del segmento elegido.

### 4. 🎮 Exploración de Videojuegos (`03_Exploracion_Juegos.py`)
Herramienta de búsqueda interactiva (por considencias en texto) para inspeccionar la salud de cualquier videojuego de la muestra:
- Indicadores clave de desempeño de manera individual.
- Posición exacta del videojuego por volumen dentro del catálogo de Steam.
- Diferencial de positividad del juego frente al promedio del mercado global.
- Gráfico evolutivo de reseñas y distribución de aportaciones de la comunidad según su idioma nativo.

### 5. 💬 Análisis de Sentimiento (`04_Analisis_Sentimiento.py`)
Integra el modelo de Machine Learning desarrollado e implementa inferencia en tiempo real:
- **Área de Texto Libre:** Escribe una reseña personalizada sobre cualquier videojuego en inglés para que el clasificador prediga si se trata de un sentimiento positivo o negativo.
- **Margen de Decisión:** Muestra la distancia geométrica al hiperplano separador del SVM.
- **Explorador de la Base:** Consulta las reseñas almacenadas en la base de datos aplicando filtros y contrasta la clasificación predictiva del modelo con la recomendación binaria original realizada por el jugador.

---

## 🛠️ Stack Tecnológico Utilizado
- **Lenguaje Principal:** Python 3.13
- **Framework de Interfaz:** Streamlit (Interacciones dinámicas y componentes de layouts)
- **Análisis y Manipulación:** Pandas, NumPy y PyArrow
- **Visualizaciones Interactivas:** Plotly Express y Plotly Graph Objects
- **Ciencia de Datos y Machine Learning:** Scikit-Learn (TF-IDF Vectorizer + Linear Support Vector Classifier), Joblib
- **Almacenamiento e Integración:** Google Drive (Almacenamiento unificado de las capas Medallion Parquet y archivos serializados)
- **Gestión de Entornos:** Pipelines validados por validación sintáctica mediante el árbol AST de Python

---

## 🚀 Instrucciones de Ejecución Local / Servidor
Sigue estos sencillos pasos para levantar la aplicación en tu máquina local o servidor cloud:

1. **Clonar el repositorio o ubicarte en el directorio raíz de Streamlit:**
   ```bash
   cd Analytics/Streamlit/
   ```
2. **Crear e inicializar un entorno virtual (Recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scriptsctivate
   ```
3. **Instalar las dependencias del proyecto:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ejecutar la aplicación con Streamlit:**
   ```bash
   streamlit run app.py
   ```
5. **Acceso Visual:**
   Abre en tu navegador la dirección URL por defecto indicada por el servidor (usualmente `http://localhost:8501`).

---

## 🏫 Información Académica e Integrantes
Este repositorio pertenece al grupo de **Deheza, Julian; Gargiulo, Franco; Girondo, Mauro**.

Corresponde al **Trabajo Práctico 3 - Unidad 7** de la materia **Infraestructura de la Tecnología** de la **Tecnicatura Universitaria en Ciencia de Datos e IA** perteneciente al área de Datos de la **Universidad del Gran Rosario** (UGR).
