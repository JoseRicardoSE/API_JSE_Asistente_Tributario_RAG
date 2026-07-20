# 🏛️ API JSE - Asistente Tributario RAG (Chile)

> **Asistente de Inteligencia Artificial especializado en normativa tributaria chilena, diseñado con arquitectura RAG avanzada para Contadores Auditores y especialistas en tributación.**

[![Estado: Activo](https://img.shields.io/badge/Estado-Activo-success.svg)](https://github.com/tu-usuario/tu-repositorio)
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-blue.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Sobre el Proyecto

Este sistema no es un chatbot tradicional; es un motor de consulta legal construido sobre la arquitectura **RAG (Retrieval-Augmented Generation)**. Garantiza precisión técnica absoluta evitando alucinaciones, ya que obliga a los modelos LLM a justificar cada respuesta citando explícitamente los cuerpos legales, su estructura jerárquica (Libro, Título, Párrafo) y sus respectivos artículos.

El proyecto ya incluye pre-cargada la **"Santísima Trinidad" del Derecho Tributario Chileno**:
* 📘 **Ley sobre Impuesto a la Renta** (DL 824)
* 📙 **Ley sobre Impuesto a las Ventas y Servicios - IVA** (DL 825)
* 📕 **Código Tributario** (DL 830)

### 📸 Demostración Visual

![Demo de la Interfaz](https://via.placeholder.com/800x400.png?text=Reemplaza+esta+imagen+con+una+captura+de+tu+app)

---

## ✨ Características Técnicas Principales (Data Engineering & AI)

* 📖 **Pipeline de Datos e Ingesta (`ingest.py`):** 
    - **Limpieza de Ruido Institucional (Regex):** Parser avanzado de expresiones regulares que limpia las imperfecciones de los documentos de la Biblioteca del Congreso Nacional (BCN), eliminando notas marginales, saltos de página y tablas HTML rotas.
    - **Estructuración Jerárquica Estricta:** Reconstrucción automática del árbol legal mediante la detección de Libros, Títulos, Párrafos, Artículos y Letras para asignarles el formato Markdown correspondiente.
    - **Inyección de Metadatos (Context Injection):** Soluciona la "amnesia de contexto" insertando la jerarquía legal exacta dentro de cada fragmento antes de vectorizarlo. Así, el LLM no pierde el contexto de la ley al analizar artículos individuales.
    - **Doble Estrategia de Chunking:** Combina un `MarkdownHeaderTextSplitter` para respetar la integridad semántica de cada Artículo, respaldado por un `RecursiveCharacterTextSplitter` de seguridad para artículos excesivamente largos.

* 🧠 **Orquestación y Motor RAG (`app.py`):**
    - **Retriever Dinámico (Top-K):** El motor ajusta matemáticamente la cantidad de documentos recuperados (chunks) basándose en la Modalidad de Consulta elegida por el usuario (`k=3` para respuestas express, `k=12` para informes).
    - **Expansión de Consulta (Query Expansion):** Intercepción de acrónimos en tiempo real (ej. "IVA" -> "Impuesto al Valor Agregado DL 825") para forzar una recuperación exacta en leyes que no utilizan siglas.
    - **Caché Inteligente Hash MD5:** Sistema de caché avanzado a nivel de backend que guarda un registro criptográfico combinando el proveedor LLM, el modelo, la temperatura, el modo y todo el historial de la conversación. Logra latencia cero y cero consumo de tokens en consultas repetidas.
    - **Soporte Multi-Modelo (Factory Pattern):** Inferencia agnóstica que permite cambiar en caliente entre Groq, Google, Cohere, HuggingFace y Ollama (modelos 100% locales).
    - **Prompt Engineering Dinámico y Anti-Alucinaciones:** Inyecta diferentes reglas de formato en tiempo de ejecución (System Prompts) según la modalidad, exigiendo siempre al LLM que justifique su respuesta usando la metadata recuperada.
* 🧠 **Embeddings Locales:** Utiliza `FastEmbed` (`paraphrase-multilingual-MiniLM-L12-v2`) ejecutándose localmente, lo que elimina el costo por token al momento de vectorizar los documentos hacia **Qdrant Cloud**.
* 🎨 **Interfaz de Usuario Avanzada (Streamlit):**
  * **Modalidades de Consulta:** Permite elegir entre 'Dato Express', 'Consulta Estándar' e 'Informe de Auditoría', ajustando dinámicamente el comportamiento del LLM.
  * **Control de Creatividad:** Ajuste de temperatura para transicionar entre respuestas estrictamente precisas (0.0) y más abiertas (1.0).
  * **Memoria de Conversación:** Opción para activar o desactivar el historial del chat, optimizando el consumo de tokens cuando no se requiere el contexto previo.
  * **Transparencia de Fuentes:** Despliega en la interfaz los documentos y artículos exactos que el modelo consultó para formular su respuesta.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnologías |
| :--- | :--- |
| **Backend & API** | FastAPI, Uvicorn, Python 3 |
| **Orquestación AI** | LangChain, LangChain-Qdrant |
| **Frontend** | Streamlit |
| **Base de Datos Vectorial** | Qdrant Cloud |
| **Embeddings** | FastEmbed (Local) |
| **Proveedores LLM** | Groq, Google GenAI, Cohere, HuggingFace, Ollama |

---

## 🚀 Guía de Instalación y Uso

Sigue estos pasos para ejecutar el proyecto en tu entorno local.

### 1. Clonar el repositorio
```bash
# RECUERDA: Cambiar la URL por la de tu repositorio real
git clone https://github.com/tu-usuario/tu-repositorio.git
cd PROYECTO_TI_TRIBUTARIO_AGENTE_RAG
```

### 2. Configurar entorno virtual (Recomendado)
```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Mac/Linux:
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto.
> ⚠️ **Importante:** Por seguridad, este archivo está en `.gitignore`. **Nunca lo subas a tu repositorio.**

```env
# Vector Database (Requerido)
QDRANT_URL=tu_url_de_qdrant_cloud
QDRANT_API_KEY=tu_api_key_de_qdrant

# LLM Providers (Deja en blanco los que no uses)
GROQ_API_KEY=tu_api_key_de_groq
GEMINI_API_KEY=tu_api_key_de_gemini
COHERE_API_KEY=tu_api_key_de_cohere
HUGGINGFACE_API_KEY=tu_api_key_de_huggingface

# Nota sobre Ollama: 
# Si usas Ollama, asegúrate de tener el motor corriendo localmente en el puerto por defecto (localhost:11434). No requiere API Key.
```

### 5. Ingesta de Documentos (Opcional, las leyes ya están en la carpeta)
Si deseas reconstruir la base de datos vectorial o agregar nuevos documentos Markdown a la carpeta `documentos_legales_md`:
```bash
python ingest.py
```
*Verás en consola cómo el script limpia la metadata de la BCN y genera los chunks estructurados.*

### 6. Ejecución de la Aplicación
Se requieren dos terminales para levantar el backend y el frontend.

**Terminal 1 (Backend - FastAPI):**
```bash
uvicorn app:app --reload
```
*La API quedará disponible en: `http://localhost:8000`*

**Terminal 2 (Frontend - Streamlit):**
```bash
streamlit run ui.py
```
*El navegador se abrirá automáticamente con la interfaz del Chat RAG.*

---

## 📬 Contacto y Soporte

- **Autor**: [José Salgado Escalona]
- **LinkedIn**: [(https://www.linkedin.com/in/jos%C3%A9-ricardo-salgado-escalona/)]

---
⭐️ *Si este proyecto te resulta útil o interesante, no dudes en dejarle una estrella en GitHub.* ⭐️
