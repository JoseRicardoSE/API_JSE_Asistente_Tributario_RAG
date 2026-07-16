import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

app = FastAPI(title="API JSE - Asistente Tributario RAG")

# Pydantic model for input
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str

# Configuración
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY]):
    raise ValueError("Faltan variables de entorno necesarias (QDRANT_URL, QDRANT_API_KEY, GROQ_API_KEY)")

# Inicializar Embeddings
embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Inicializar Qdrant
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
vector_store = QdrantVectorStore(
    client=client,
    collection_name="base_conocimiento_tributario",
    embedding=embeddings,
)

retriever = vector_store.as_retriever(search_kwargs={"k": 15})

# Inicializar LLM Groq
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY
)

# Template del Prompt
system_prompt = """Eres un Auditor y Consultor Tributario experto de Chile/Latinoamérica.
Tu tarea es analizar detalladamente las normativas proporcionadas y responder a las consultas del usuario con un nivel técnico, completo y bien estructurado (usando viñetas si es necesario).

Reglas obligatorias:
1. Responde ÚNICAMENTE utilizando la información del contexto recuperado. Puedes usar tu conocimiento para hilar y explicar profesionalmente la respuesta, pero los datos duros y reglas tributarias DEBEN provenir del contexto.
2. Cada vez que menciones una regla o condición, DEBES citar la fuente agregando al final de tu respuesta el valor del metadato 'referencia_cita' de los documentos utilizados. (ejemplo: Referencias: [referencia 1], [referencia 2])
3. Si el contexto no contiene información suficiente o relevante para responder con certeza, responde exactamente: "La normativa actual en mi base de datos no menciona esto." No alucines información contable, legal o tributaria.
4. Desarrolla tus respuestas: no des respuestas cortas. Explica el tratamiento tributario, implicancias y requisitos según el contexto.

Contexto:
{context}"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{question}")
])

def format_docs(docs):
    formatted_docs = []
    for doc in docs:
        ref = doc.metadata.get("referencia_cita", "Referencia desconocida")
        formatted_docs.append(f"Contenido: {doc.page_content}\nMetadatos (referencia_cita): {ref}")
    return "\n\n".join(formatted_docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response = await rag_chain.ainvoke(request.query)
        return ChatResponse(answer=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
