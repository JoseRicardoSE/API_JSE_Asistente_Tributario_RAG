import streamlit as st
import requests

st.set_page_config(page_title="JoseSE", page_icon="⚖️")

st.title("API JSE - Asistente Tributario RAG")

API_URL = "http://localhost:8000/chat"

# Inicializar el historial del chat en session_state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar el historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar el input del usuario
if prompt := st.chat_input("Ingresa tu consulta tributaria..."):
    # Mostrar el mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Realizar petición al backend
    with st.chat_message("assistant"):
        with st.spinner("Consultando normativas..."):
            try:
                response = requests.post(API_URL, json={"query": prompt})
                response.raise_for_status()
                answer = response.json().get("answer", "No se recibió respuesta.")
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except requests.exceptions.RequestException as e:
                error_msg = f"Error al comunicarse con el servidor: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
