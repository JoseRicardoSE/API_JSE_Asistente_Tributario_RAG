import streamlit as st
import requests

st.set_page_config(page_title="JoseSE RAG", page_icon="⚖️")

# --- MAPEO DE MODELOS ---
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

# --- SIDEBAR: NUEVO CHAT ---
with st.sidebar:
    st.title("Opciones")
    selected_model_label = st.selectbox(
        "🤖 Elegir Modelo de IA",
        list(MODEL_OPTIONS.keys())
    )
    
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

    temperature = st.slider("🌡️ Temperatura (Creatividad)", min_value=0.0, max_value=1.0, value=0.0, step=0.1, help="0.0 = Preciso y estricto. 1.0 = Creativo.")
    use_memory = st.toggle("🧠 Recordar Historial", value=True, help="Si lo desactivas, el bot no recordará los mensajes anteriores, ahorrando muchísimos tokens.")
    if st.button("🗑️ Limpiar Conversación / Nuevo Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hola, soy tu asistente tributario. ¿En qué te puedo ayudar hoy?"}
        ]
        st.rerun()

st.title("API JSE - Asistente Tributario RAG")

API_URL = "http://localhost:8000/chat"

# Inicializar el historial del chat en session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy tu asistente tributario. ¿En qué te puedo ayudar hoy?"}
    ]

# Mostrar el historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar el input del usuario
if prompt := st.chat_input("Ej: ¿Qué es el IVA y cuál es su tasa?"):
    
    # Mostrar el mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Realizar petición al backend
    with st.chat_message("assistant"):
        with st.spinner("Consultando normativas y analizando historial..."):
            try:
                provider = MODEL_OPTIONS[selected_model_label]["provider"]
                model_name = MODEL_OPTIONS[selected_model_label]["model_name"]
                
                if use_memory:
                    payload = {
                        "messages": st.session_state.messages,
                        "provider": provider,
                        "model_name": model_name,
                        "temperature": temperature,
                        "mode": mode
                    }
                else:
                    payload = {
                        "messages": [st.session_state.messages[-1]],
                        "provider": provider,
                        "model_name": model_name,
                        "temperature": temperature,
                        "mode": mode
                    }
                    
                response = requests.post(API_URL, json=payload)
                response.raise_for_status()
                
                data = response.json()
                answer = data.get("answer", "No se recibió respuesta.")
                sources = data.get("sources", [])

                st.markdown(answer)
                
                if sources:
                    with st.expander("📚 Documentos analizados para esta respuesta"):
                        for source in sources:
                            st.caption(f"- {source}")

                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Error al comunicarse con el servidor: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
