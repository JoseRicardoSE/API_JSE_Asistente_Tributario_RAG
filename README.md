# API JSE - Asistente Tributario RAG

Asistente de Inteligencia Artificial especializado en normativa tributaria (Chile / Latinoamérica), diseñado específicamente para Contadores Auditores y especialistas en tributación.

![Demo de la Interfaz](https://via.placeholder.com/800x400.png?text=Reemplaza+esta+imagen+con+una+captura+de+tu+app)

El sistema utiliza la arquitectura **RAG (Retrieval-Augmented Generation)** para garantizar precisión técnica, evitando alucinaciones y obligando al modelo a justificar sus respuestas citando explícitamente los cuerpos legales (Leyes, Circulares, Resoluciones) y sus respectivas páginas.

## Características Principales

* **Cero Alucinaciones:** El modelo responde únicamente basándose en la documentación legal provista. Si no lo sabe, no lo inventa.
* **Precisión de Auditor:** Emplea Llama 3.3 (70B) para procesar el texto y redactar respuestas estructuradas, técnicas y fundamentadas (ideal para Operación Renta, Reorganizaciones, etc.).
* **Rápido y Eficiente:** Usa `FastEmbed` (local) para la vectorización rápida y `Qdrant Cloud` para la búsqueda semántica.
* **Trazabilidad Legal:** Cada respuesta incluye la referencia exacta (Ej: `[Ley: ley_de_la_renta_dl824.pdf, Pág. 32]`).

## Arquitectura y Stack Tecnológico

* **Backend:** FastAPI, LangChain, Uvicorn.
* **Frontend:** Streamlit.
* **Base de Datos Vectorial:** Qdrant Cloud.
* **LLM:** Groq (Llama 3.3 70B Versatile).
* **Embeddings:** FastEmbed (`paraphrase-multilingual-MiniLM-L12-v2`).

## Estructura del Proyecto

* `ingest.py`: Script para cargar documentos PDF, inyectar metadatos estructurados, crear los embeddings y subir la data a Qdrant.
* `app.py`: Backend con FastAPI que aloja el motor de inferencia (Cadena RAG) y expone el endpoint `/chat`.
* `ui.py`: Frontend interactivo en Streamlit para que el usuario consulte al asistente.
* `requirements.txt`: Dependencias necesarias del proyecto.

## Instrucciones de Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/tu-repositorio.git
   cd PROYECTO_TI_TRIBUTARIO_AGENTE_RAG
   ```

2. Crea y activa un entorno virtual (recomendado):
   ```bash
   python -m venv .venv
   
   # En Windows:
   .venv\Scripts\activate
   
   # En Mac/Linux:
   source .venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura tus variables de entorno:
   Crea un archivo `.env` en la raíz del proyecto y agrega tus API Keys **(no lo subas a GitHub)**:
   ```env
   QDRANT_URL=tu_url_de_qdrant_cloud
   QDRANT_API_KEY=tu_api_key_de_qdrant
   GROQ_API_KEY=tu_api_key_de_groq
   ```

5. Carga tus documentos legales:
   Crea una carpeta llamada `documentos_legales` en la raíz del proyecto, deposita ahí tus leyes/circulares en formato PDF y ejecuta la ingesta:
   ```bash
   python ingest.py
   ```

## Ejecución del Proyecto

Para ejecutar la aplicación localmente, necesitas levantar tanto el backend como el frontend en terminales separadas.

**Terminal 1 (Backend - FastAPI):**
```bash
uvicorn app:app --reload
```
*La API quedará disponible en http://localhost:8000*

**Terminal 2 (Frontend - Streamlit):**
```bash
streamlit run ui.py
```
*Se abrirá automáticamente el navegador con la interfaz del chat.*
