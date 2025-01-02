import streamlit as st
from pathlib import Path
from document_processor import DocumentProcessor
from embedding_manager import EmbeddingManager
from rag_pipeline import RAGPipeline
from voice_handler import VoiceHandler
import logging
import time

logger = logging.getLogger(__name__)

class StreamlitRAGApp:
    def __init__(self):
        self.setup_environment()
        self.initialize_session_state()
        self.voice_handler = VoiceHandler()
        self.setup_ui()

    def initialize_session_state(self):
        """Initialize session state variables"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "rag_pipeline" not in st.session_state:
            st.session_state.rag_pipeline = None
        if "language" not in st.session_state:
            st.session_state.language = "en"
        if "voice_enabled" not in st.session_state:
            st.session_state.voice_enabled = False

    def setup_ui(self):
        """Setup the Streamlit UI"""
        with st.sidebar:
            # ... (previous sidebar code) ...

            st.markdown("### Language Settings")
            language = st.selectbox(
                "Select Language",
                ["English", "नेपाली"],
                index=0
            )
            st.session_state.language = "en" if language == "English" else "ne"

            voice_enabled = st.checkbox("Enable Voice Interface", value=st.session_state.voice_enabled)
            st.session_state.voice_enabled = voice_enabled

        # Main chat interface
        st.title("BYD Nepal AI Assistant")

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                content = message["content"]
                if st.session_state.language == "ne" and message["role"] == "assistant":
                    content = self.voice_handler.translate_text(content, "ne")
                st.markdown(content)
                
                # Play voice response if enabled
                if st.session_state.voice_enabled and message["role"] == "assistant":
                    lang = "ne" if st.session_state.language == "ne" else "en"
                    self.voice_handler.text_to_speech(content, lang)

        # Voice input button
        if st.session_state.voice_enabled:
            if st.button("🎤 Speak"):
                with st.spinner("Listening..."):
                    lang = "ne-NP" if st.session_state.language == "ne" else "en-US"
                    voice_input = self.voice_handler.speech_to_text(lang)
                    if voice_input:
                        self.process_input(voice_input)

        # Text input
        if prompt := st.chat_input("Type your question here..."):
            self.process_input(prompt)

    def process_input(self, input_text):
        """Process user input (voice or text)"""
        st.session_state.messages.append({"role": "user", "content": input_text})
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            try:
                result = st.session_state.rag_pipeline.query(input_text)
                response = result["answer"]
                
                # Translate if needed
                if st.session_state.language == "ne":
                    response = self.voice_handler.translate_text(response, "ne")
                
                message_placeholder.markdown(response)
                
                # Play voice response if enabled
                if st.session_state.voice_enabled:
                    lang = "ne" if st.session_state.language == "ne" else "en"
                    self.voice_handler.text_to_speech(response, lang)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                message_placeholder.error("An error occurred. Please try again.")

if __name__ == "__main__":
    st.set_page_config(
        page_title="BYD Nepal AI Assistant",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS for voice button
    st.markdown("""
        <style>
        .stButton button {
            background-color: #ff4b4b;
            color: white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            padding: 10px;
            font-size: 24px;
            margin: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    app = StreamlitRAGApp()