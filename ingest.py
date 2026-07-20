import os
import re
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "base_conocimiento_tributario"

def clean_and_format_text(text: str) -> str:
    # 1. Limpieza de Ruido Institucional y Notas Marginales
    text = re.sub(r'Biblioteca del Congreso Nacional de Chile.*?página \d+ de \d+\s*', '', text)
    text = re.sub(r'Biblioteca del Congreso Nacional de Chile / BCN\s*', '', text)
    text = re.sub(r'\d+\s+Biblioteca del Congreso.*?Ley Chile\s*', '', text)
    text = re.sub(r'\d+\s+años?\s*', '', text)
    text = re.sub(r'Decreto Ley \d+, HACIENDA \(\d+\)\s*', '', text)
    text = re.sub(r'Ley Chile\s*', '', text)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)  # orphan numbers
    
    # Eliminar Notas Marginales de Modificaciones (ej. Ley 21210 D.O. 24.02.2020) y Bloques NOTA:
    # IMPORTANTE: Usamos ^\s*(?:## )?NOTA\b para NO atrapar palabras como 'notas de débito'.
    text = re.sub(r'^\s*(?:## )?NOTA:?.*?(?=\n\n|\n[A-Z]|\n#)', '', text, flags=re.MULTILINE | re.DOTALL) 
    text = re.sub(r'Ley\s+\d+[\s\S]{1,50}?D\.O\.\s+\d{2}\.\d{2}\.\d{4}', '', text, flags=re.IGNORECASE)
    
    # 2. Limpieza de Tablas HTML rotas (Strip HTML tags)
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 3. Estructuración Jerárquica Markdown Estricta
    text = re.sub(r'^\s*(LIBRO\s+.*?)$', r'# \1', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*(DISPOSICIONES?\s+TRANSITORIAS?.*?)$', r'# \1', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*(T[IÍ\w]*TULO\s+.*?)$', r'## \1', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*(P[AÁ\w]*RRAFO\s+.*?)$', r'### \1', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Separar Artículos (Header 4)
    text = re.sub(r'^\s*(ART[IÍ\w]*CULO|Art\.)\s+([A-Za-z0-9°]+(?:\s+bis|\s+ter)?)[.-]*\s*(.*)$', r'#### \1 \2\n\3', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # 4. Granularidad en Artículos Extensos (Header 5 para Letras a), b), A.-, B.-)
    # Detecta "a) ", "A.- " al inicio de línea
    text = re.sub(r'^\s*([a-zA-Z])[\)\.-]+\s+(.*?)$', r'##### Letra \1)\n\2', text, flags=re.MULTILINE)
    
    return text

def main():
    # 1. Cargar archivos Markdown
    directorio_md = "documentos_legales_md" 
    if not os.path.exists(directorio_md):
        print(f"Advertencia: La carpeta '{directorio_md}' no existe.")
        return

    # 2. Configurar los Splitters
    # Primer Splitter: Semántico (Por títulos de Markdown)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # Segundo Splitter: De seguridad (Por tamaño de caracteres para artículos gigantes)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, 
        chunk_overlap=200
    )

    print(f"Cargando documentos Markdown desde {directorio_md}...")
    loader = DirectoryLoader(directorio_md, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()

    all_chunks = []
    for doc in docs:
        # Limpiar y estructurar el texto
        cleaned_text = clean_and_format_text(doc.page_content)
        
        # Partir el doc en base a los encabezados Markdown
        docs_raw = markdown_splitter.split_text(cleaned_text)
        
        # INYECCIÓN DE CONTEXTO (Para que la IA sepa de qué trata el artículo o la letra)
        for sub_doc in docs_raw:
            context_headers = []
            for i in range(1, 6):
                header_val = sub_doc.metadata.get(f'Header {i}')
                if header_val:
                    context_headers.append(header_val)
            
            if context_headers:
                jerarquia = " > ".join(context_headers)
                sub_doc.page_content = f"[Contexto Legal: {jerarquia}]\n{sub_doc.page_content}"
                
        # Splitter de seguridad (por tamaño)
        final_splits = text_splitter.split_documents(docs_raw)
        
        # Inyectar metadatos base a cada fragmento final
        for split in final_splits:
            nombre_archivo = os.path.basename(doc.metadata.get("source", "desconocido"))
            split.metadata["documento_origen"] = nombre_archivo
            
            # Armamos una cita hermosa usando el Título que detectó Markdown
            titulo_seccion = split.metadata.get('Header 4', 
                                split.metadata.get('Header 3', 
                                    split.metadata.get('Header 2', 
                                        split.metadata.get('Header 1', 'Seccion Legal'))))
            
            # Aseguramos que la cita tenga un formato limpio para el frontend
            split.metadata["referencia_cita"] = f"{titulo_seccion} ({nombre_archivo})"
            
            all_chunks.append(split)

    print(f"Se crearon {len(all_chunks)} fragmentos estructurados y ligeros.")
    
    # Inicializar embeddings
    print("Inicializando modelo de embeddings...")
    embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    print("Subiendo a Qdrant...")
    QdrantVectorStore.from_documents(
        all_chunks,
        embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
        force_recreate=True
    )
    print("Ingesta de Markdown profesional completada.")

if __name__ == "__main__":
    main()