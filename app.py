import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
import hashlib
import re

# LLM Providers
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_cohere import ChatCohere
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

load_dotenv()

app = FastAPI(title="API JSE - Asistente Tributario RAG Multi-Modelo")

# --- Pydantic Models ---
class MessageModel(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[MessageModel]
    provider: str = "groq"
    model_name: str = "llama-3.3-70b-versatile"
    temperature: float = 0.0
    mode: str = "estandar"

class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []

# --- Configuración y Base Vectorial ---
query_cache = {}

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not all([QDRANT_URL, QDRANT_API_KEY]):
    raise ValueError("Faltan variables de entorno necesarias para Qdrant.")

embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
vector_store = QdrantVectorStore(
    client=client,
    collection_name="base_conocimiento_tributario",
    embedding=embeddings,
)
# Nota: El retriever ahora se instancia dinámicamente dentro de chat_endpoint

# --- Fábrica de Modelos LLM ---
def get_llm(provider: str, model_name: str, temperature: float = 0.0):
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key: raise ValueError("Falta GROQ_API_KEY en .env")
        return ChatGroq(temperature=temperature, model_name=model_name, api_key=api_key)
    elif provider == "google":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("Falta GEMINI_API_KEY en .env")
        return ChatGoogleGenerativeAI(temperature=temperature, model=model_name, google_api_key=api_key)
    elif provider == "cohere":
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key: raise ValueError("Falta COHERE_API_KEY en .env")
        return ChatCohere(temperature=temperature, model=model_name, cohere_api_key=api_key)
    elif provider == "ollama":
        # Ollama se conecta de forma local (por defecto a localhost:11434)
        return ChatOllama(model=model_name, temperature=temperature)
    elif provider == "huggingface":
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key: raise ValueError("Falta HUGGINGFACE_API_KEY en .env")
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

# --- Prompt ---
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

prompt = ChatPromptTemplate.from_messages([
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

# --- Endpoint ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_query = request.messages[-1].content
        
        # Caché Seguro: Ahora incluye el provider, model, mode y temperature
        history_str = "|".join([f"{m.role}:{m.content}" for m in request.messages])
        cache_key_raw = f"{request.provider}:{request.model_name}:{request.mode}:{request.temperature}:{history_str}"
        cache_key = hashlib.md5(cache_key_raw.encode()).hexdigest()
        
        if cache_key in query_cache:
            print(f"⚡ Respuesta servida desde Caché ({request.model_name} - {request.mode})!")
            return query_cache[cache_key]

        # 1. Recuperar contexto (Retriever dinámico según modalidad)
        k_values = {"express": 3, "estandar": 8, "informe": 12}
        k_limit = k_values.get(request.mode, 8)
        retriever = vector_store.as_retriever(search_kwargs={"k": k_limit})
        
        # Expansión de consulta (Solución a falta de acrónimos en textos legales crudos)
        search_query = user_query
        if re.search(r'\b(iva|ventas y servicios)\b', search_query, re.IGNORECASE):
            search_query = search_query + " Impuesto al Valor Agregado DL 825 tasa 19%"
        if re.search(r'\brenta\b', search_query, re.IGNORECASE):
            search_query = search_query + " Impuesto a la Renta DL 824"
        if re.search(r'\bsii\b', search_query, re.IGNORECASE):
            search_query = search_query + " Servicio de Impuestos Internos"
            
        docs = await retriever.ainvoke(search_query)
        context_text = format_docs(docs)
        fuentes_unicas = list(set([doc.metadata.get("referencia_cita", "Desconocida") for doc in docs]))

        # 2. Construir historial (Solo 4 últimos mensajes)
        chat_history = []
        for msg in request.messages[-5:-1]:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                chat_history.append(AIMessage(content=msg.content))

        # 3. Construir Instrucciones de Modalidad
        if request.mode == "express":
            mode_instructions = "Sé muy conciso (2 o 3 líneas máximo). Ve directo al dato duro. ES OBLIGATORIO incluir la 'referencia_cita' al final de tu respuesta corta."
        elif request.mode == "informe":
            mode_instructions = "Estructura tu respuesta en 4 secciones formales: 1. Resumen Ejecutivo, 2. Base Legal (Lista aquí los 'Metadatos (referencia_cita)' encontrados), 3. Análisis Técnico Detallado, 4. Implicancias Prácticas."
        else:
            mode_instructions = "Desarrolla tu respuesta: no des respuestas excesivamente cortas. Explica el tratamiento tributario, implicancias y requisitos, asegurándote de incrustar la 'referencia_cita' de forma natural en tu explicación."

        # 4. Inicializar LLM Dinámicamente
        llm = get_llm(request.provider, request.model_name, request.temperature)
        rag_chain = prompt | llm | StrOutputParser()

        # 5. Generar respuesta
        answer = await rag_chain.ainvoke({
            "question": user_query,
            "context": context_text,
            "chat_history": chat_history,
            "mode_instructions": mode_instructions
        })
        
        response_data = ChatResponse(answer=answer, sources=fuentes_unicas)
        query_cache[cache_key] = response_data
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
