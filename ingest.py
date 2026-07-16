import os
from dotenv import load_dotenv

# Librerías de LangChain y herramientas de IA
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore

# 1. Cargar variables de entorno (Credenciales)
# Crea un archivo .env en la misma carpeta con QDRANT_URL y QDRANT_API_KEY
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "base_conocimiento_tributario"

def main():
    print("🚀 Iniciando el proceso de Ingesta Profesional RAG...")

    # =========================================================================
    # PASO 1: CARGA DE DOCUMENTOS
    # =========================================================================
    # Asume que tienes una carpeta llamada "documentos_legales" con tus PDFs
    directorio_pdfs = "documentos_legales"
    
    if not os.path.exists(directorio_pdfs):
        os.makedirs(directorio_pdfs)
        print(f"⚠️ Carpeta '{directorio_pdfs}' creada. Por favor, coloca tus PDFs legales ahí y vuelve a ejecutar.")
        return

    print(f"📄 Leyendo PDFs desde la carpeta '{directorio_pdfs}'...")
    loader = PyPDFDirectoryLoader(directorio_pdfs)
    docs = loader.load()

    if not docs:
        print("❌ No se encontraron documentos PDF. Abortando.")
        return
    
    print(f"✅ Se cargaron {len(docs)} páginas en total.")

    # =========================================================================
    # PASO 2: INYECCIÓN DE METADATOS (Tu Diferenciador Competitivo)
    # =========================================================================
    # Aquí es donde le damos la estructura para que la IA no alucine y cite bien.
    print("🏷️  Inyectando metadatos avanzados a cada página...")
    for doc in docs:
        # Extraer el nombre del archivo original
        source_path = doc.metadata.get("source", "documento_desconocido.pdf")
        nombre_archivo = os.path.basename(source_path)
        
        # Página real (sumamos 1 porque la librería empieza en 0)
        pagina_real = doc.metadata.get("page", 0) + 1
        
        # Clasificador automático simple basado en el nombre del archivo
        tipo_norma = "General"
        if "ley" in nombre_archivo.lower():
            tipo_norma = "Ley"
        elif "resolucion" in nombre_archivo.lower() or "res" in nombre_archivo.lower():
            tipo_norma = "Resolución SII"
        elif "circular" in nombre_archivo.lower():
            tipo_norma = "Circular SII"

        # Guardamos la metadata limpia y estructurada
        doc.metadata = {
            "documento_origen": nombre_archivo,
            "pagina": pagina_real,
            "tipo_norma": tipo_norma,
            # Añadimos un texto de cita pre-fabricado para que la IA lo use fácilmente
            "referencia_cita": f"[{tipo_norma}: {nombre_archivo}, Pág. {pagina_real}]"
        }

    # =========================================================================
    # PASO 3: CHUNKING INTELIGENTE
    # =========================================================================
    # No cortamos palabras por la mitad. Intentamos respetar los párrafos dobles (\n\n)
    # que usualmente separan artículos o incisos en las leyes.
    print("✂️  Dividiendo los documentos en fragmentos (Chunks)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # Tamaño ideal para que la IA tenga buen contexto
        chunk_overlap=150,    # Solapamiento para no perder la idea entre cortes
        separators=["\n\n", "\n", ".", " ", ""] 
    )
    
    chunks = text_splitter.split_documents(docs)
    print(f"✅ Los documentos se dividieron en {len(chunks)} fragmentos útiles.")

    # =========================================================================
    # PASO 4: EMBEDDINGS VECTORIALES (El Motor Rápido)
    # =========================================================================
    # Usamos un modelo Multilingüe excelente para español. 
    # Al usar FastEmbed, esto corre localmente en tu CPU usando Rust. Es GRATIS.
    print("🧠 Inicializando motor de Embeddings Multilingüe...")
    embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    # =========================================================================
    # PASO 5: SUBIDA A QDRANT CLOUD
    # =========================================================================
    print(f"☁️  Subiendo {len(chunks)} fragmentos a Qdrant Cloud (Colección: {COLLECTION_NAME})...")
    print("⏳ Esto puede tardar unos minutos dependiendo de la cantidad de PDFs...")
    
    # force_recreate=True borra la base de datos anterior y la crea de nuevo.
    # Útil mientras estás desarrollando y subiendo PDFs nuevos.
    QdrantVectorStore.from_documents(
        chunks,
        embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
        force_recreate=True 
    )

    print("🎉 ¡Ingesta completada con éxito! Tu base de datos vectorial está lista para responder preguntas.")

if __name__ == "__main__":
    main()