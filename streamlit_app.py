import streamlit as st
import os
import hashlib
import re
from dotenv import load_dotenv

# Langchain and Qdrant imports
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

# LLM Providers
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_cohere import ChatCohere
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

st.set_page_config(page_title="API JSE - RAG Tributario", page_icon="⚖️")

load_dotenv()

# --- Cache memory for responses ---
if "query_cache" not in st.session_state:
    st.session_state.query_cache = {}

# --- Initialization of Vector DB ---
@st.cache_resource
def get_vector_store():
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    
    if not all([QDRANT_URL, QDRANT_API_KEY]):
        # Si corremos en Streamlit Cloud, los secretos se inyectan en os.environ automáticamente si están configurados.
        st.error("Faltan variables de entorno necesarias para Qdrant. Configúralas en los Secrets de Streamlit.")
        st.stop()
        
    embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    return QdrantVectorStore(
        client=client,
        collection_name="base_conocimiento_tributario",
        embedding=embeddings,
    )

vector_store = get_vector_store()

# --- Fábrica de Modelos LLM ---
def get_llm(provider: str, model_name: str, temperature: float = 0.0):
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key: raise ValueError("Falta GROQ_API_KEY en .env o Secrets")
        return ChatGroq(temperature=temperature, model_name=model_name, api_key=api_key)
    elif provider == "google":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("Falta GEMINI_API_KEY en .env o Secrets")
        return ChatGoogleGenerativeAI(temperature=temperature, model=model_name, google_api_key=api_key)
    elif provider == "cohere":
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key: raise ValueError("Falta COHERE_API_KEY en .env o Secrets")
        return ChatCohere(temperature=temperature, model=model_name, cohere_api_key=api_key)
    elif provider == "ollama":
        return ChatOllama(model=model_name, temperature=temperature)
    elif provider == "huggingface":
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key: raise ValueError("Falta HUGGINGFACE_API_KEY en .env o Secrets")
        llm = HuggingFaceEndpoint(
            repo_id=model_name,
            task="text-generation",
            max_new_tokens=1024,
            huggingfacehub_api_token=api_key,
            temperature=temperature if temperature > 0 else 0.01
        )
        return ChatHuggingFace(llm=llm)
    else:
        raise ValueError(f"Proveedor no soportado: {provider}")

# --- Prompt System ---
system_prompt = """Eres un Auditor y Consultor Tributario experto de Chile/Latinoamérica.
Tu tarea es analizar detalladamente las normativas proporcionadas en el "Contexto recuperado" y responder a las consultas del usuario.

Reglas obligatorias (Cero Alucinaciones):
1. Responde ÚNICAMENTE utilizando la información de los fragmentos de texto del contexto.
2. CITA OBLIGATORIA: Los documentos legales fueron procesados y tienen un campo llamado 'Metadatos (referencia_cita)'. Cada vez que menciones una regla, DEBES citar exactamente ese valor. Ejemplo de formato esperado: "De acuerdo al ARTÍCULO 20 (ley_sobre_impuesto_a_la_renta_dl824.md)...". No inventes leyes, usa el nombre exacto del archivo MD.
3. EXCEPCIÓN MATEMÁTICA Y CUANTITATIVA: Si el usuario te pide un cálculo, un ejemplo numérico o te pregunta por cantidades, TIENES PERMITIDO usar tus capacidades matemáticas para resolver el problema basándote en las tasas (ej. 19%), plazos o montos extraídos del contexto. Esto NO se considerará alucinación.
4. Si el contexto no contiene información para responder, di: "La normativa actual en mi base de datos no menciona esto." No alucines información externa.

Glosario Tributario (Conocimiento Base):
- IVA = Impuesto al Valor Agregado = Impuesto a las Ventas y Servicios (DL 825).
- Renta = Impuesto a la Renta (DL 824).
- Código Tributario (DL 830).
- ADVERTENCIA DEL SII: Los términos extraídos del 'glosario_sii.md' no reemplazan ni modifican las definiciones legales estrictas. Úsalos solo como referencia de apoyo.

Instrucciones de Formato según Modalidad:
{mode_instructions}

Contexto recuperado:
{context}"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

def format_docs(docs):
    formatted_docs = []
    for doc in docs:
        ref = doc.metadata.get("referencia_cita", "Referencia desconocida")
        formatted_docs.append(f"Contenido: {doc.page_content}\nMetadatos (referencia_cita): {ref}")
    return "\n\n".join(formatted_docs)


# --- INTERFAZ STREAMLIT ---

# Mapeo de Modelos
MODEL_OPTIONS = {
    "Groq - Llama 3.3 (70B)": {"provider": "groq", "model_name": "llama-3.3-70b-versatile"},
    "Groq - Llama 3.1 (8B)": {"provider": "groq", "model_name": "llama-3.1-8b-instant"},
    "Google - Gemini 2.5 Flash": {"provider": "google", "model_name": "gemini-2.5-flash"},
    "Cohere - Command R": {"provider": "cohere", "model_name": "command-r"},
    "Ollama - Llama 3 (8B)": {"provider": "ollama", "model_name": "llama3"},
    "Ollama - Llama 3.2 (3B)": {"provider": "ollama", "model_name": "llama3.2"},
    "Ollama - Phi 3 (Mini)": {"provider": "ollama", "model_name": "phi3"},
    "HuggingFace - Mistral 7B": {"provider": "huggingface", "model_name": "mistralai/Mistral-7B-Instruct-v0.2"},
    "HuggingFace - Zephyr 7B": {"provider": "huggingface", "model_name": "HuggingFaceH4/zephyr-7b-beta"}
}

with st.sidebar:
    st.title("Opciones")
    selected_model_label = st.selectbox("🤖 Elegir Modelo de IA", list(MODEL_OPTIONS.keys()))
    
    mode_options = {
        "⚡ Dato Express": "express",
        "⚖️ Consulta Estándar": "estandar",
        "📋 Informe de Auditoría": "informe"
    }
    selected_mode_label = st.select_slider(
        "🎚️ Modalidad de Consulta",
        options=list(mode_options.keys()),
        value="⚖️ Consulta Estándar",
        help="Express (Corto y rápido), Estándar (Equilibrado), Informe (Estructurado y exhaustivo)."
    )
    mode = mode_options[selected_mode_label]

    temperature = st.slider("🌡️ Temperatura (Creatividad)", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
    use_memory = st.toggle("🧠 Recordar Historial", value=True)
    
    if st.button("🗑️ Limpiar Conversación / Nuevo Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hola, soy tu asistente tributario. ¿En qué te puedo ayudar hoy?"}
        ]
        st.rerun()

st.title("API JSE - Asistente Tributario RAG")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy tu asistente tributario. ¿En qué te puedo ayudar hoy?"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Ej: ¿Qué es el IVA y cuál es su tasa?"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Consultando normativas y analizando historial..."):
            try:
                provider = MODEL_OPTIONS[selected_model_label]["provider"]
                model_name = MODEL_OPTIONS[selected_model_label]["model_name"]
                
                # Setup messages for LLM
                llm_messages = st.session_state.messages if use_memory else [st.session_state.messages[-1]]
                
                # Check Cache
                history_str = "|".join([f"{m['role']}:{m['content']}" for m in llm_messages])
                cache_key_raw = f"{provider}:{model_name}:{mode}:{temperature}:{history_str}"
                cache_key = hashlib.md5(cache_key_raw.encode()).hexdigest()
                
                if cache_key in st.session_state.query_cache:
                    cached_data = st.session_state.query_cache[cache_key]
                    answer = cached_data["answer"]
                    sources = cached_data["sources"]
                else:
                    # 1. Recuperar contexto
                    k_values = {"express": 3, "estandar": 8, "informe": 12}
                    k_limit = k_values.get(mode, 8)
                    retriever = vector_store.as_retriever(search_kwargs={"k": k_limit})
                    
                    search_query = user_input
                    if re.search(r'\b(iva|ventas y servicios)\b', search_query, re.IGNORECASE):
                        search_query += " Impuesto al Valor Agregado DL 825 tasa 19%"
                    if re.search(r'\brenta\b', search_query, re.IGNORECASE):
                        search_query += " Impuesto a la Renta DL 824"
                    if re.search(r'\bsii\b', search_query, re.IGNORECASE):
                        search_query += " Servicio de Impuestos Internos"
                        
                    docs = retriever.invoke(search_query) # síncrono para Streamlit Cloud
                    context_text = format_docs(docs)
                    fuentes_unicas = list(set([doc.metadata.get("referencia_cita", "Desconocida") for doc in docs]))
                    
                    # 2. Construir historial
                    chat_history = []
                    for msg in llm_messages[-5:-1]:
                        if msg["role"] == "user":
                            chat_history.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            chat_history.append(AIMessage(content=msg["content"]))
                            
                    # 3. Instrucciones de modalidad
                    if mode == "express":
                        mode_instructions = "Sé muy conciso (2 o 3 líneas máximo). Ve directo al dato duro. ES OBLIGATORIO incluir la 'referencia_cita' al final de tu respuesta corta."
                    elif mode == "informe":
                        mode_instructions = "Estructura tu respuesta en 4 secciones formales: 1. Resumen Ejecutivo, 2. Base Legal (Lista aquí los 'Metadatos (referencia_cita)' encontrados), 3. Análisis Técnico Detallado, 4. Implicancias Prácticas."
                    else:
                        mode_instructions = "Desarrolla tu respuesta: no des respuestas excesivamente cortas. Explica el tratamiento tributario, implicancias y requisitos, asegurándote de incrustar la 'referencia_cita' de forma natural en tu explicación."
                        
                    # 4. Generar respuesta
                    llm = get_llm(provider, model_name, temperature)
                    rag_chain = prompt_template | llm | StrOutputParser()
                    
                    answer = rag_chain.invoke({
                        "question": user_input,
                        "context": context_text,
                        "chat_history": chat_history,
                        "mode_instructions": mode_instructions
                    })
                    sources = fuentes_unicas
                    
                    # Guardar en caché
                    st.session_state.query_cache[cache_key] = {"answer": answer, "sources": sources}

                # Mostrar la respuesta
                st.markdown(answer)
                
                if sources:
                    with st.expander("📚 Documentos analizados para esta respuesta"):
                        for source in sources:
                            st.caption(f"- {source}")
                            
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except Exception as e:
                st.error(f"Ocurrió un error: {str(e)}")
