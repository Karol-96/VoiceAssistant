import streamlit as st
import os
import time
from pathlib import Path
# Fix imports to use relative paths
from document_processor import DocumentProcessor
from embedding_manager import EmbeddingManager
from rag_pipeline import RAGPipeline
from dotenv import load_dotenv
import logging
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAI
from langchain_core.documents import Document  

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamlitRAGApp:
    def __init__(self):
        self.setup_environment()
        self.initialize_session_state()
        self.setup_ui()
        
    def setup_environment(self):
        """Setup environment variables and configurations"""
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OpenAI API key not found. Please check your .env file.")
            st.stop()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "rag_pipeline" not in st.session_state:
            st.session_state.rag_pipeline = None
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
    def setup_ui(self):
        """Setup the Streamlit UI"""
        # Sidebar
        with st.sidebar:
            st.image("/Users/karolbhandari/Desktop/Customer Care/rag_project/RAG/logo.png", width=200)
            st.title("BYD Nepal AI Assistant")
            st.title("Powered by Cimex Nepal")
            st.markdown("---")
            
            st.markdown("### About")
            st.markdown("""
            This AI assistant helps you find information about BYD Nepal's products and services.
            
            **Features:**
            - Contextual Responses
            - Conversation Memory
            """)
        
        # Main chat interface
        st.title("BYD Nepal AI Assistant")
        
        # Initialize RAG pipeline if not already done
        if "rag_pipeline" not in st.session_state or st.session_state.rag_pipeline is None:
            try:
                # Initialize components
                embedding_manager = EmbeddingManager()
                
                # Load the existing vector store
                vector_store = embedding_manager.create_or_load_vector_store()
                
                if vector_store is None:
                    st.error("Vector store not found. Please run main.py first to initialize the database.")
                    st.stop()
                
                # Initialize RAG pipeline
                st.session_state.rag_pipeline = RAGPipeline(vector_store)
                logger.info("RAG pipeline initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing RAG pipeline: {str(e)}")
                st.error("Error initializing the assistant. Please check if main.py has been run first.")
                st.stop()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "sources" in message:
                    with st.expander("View Sources"):
                        st.markdown(message["sources"])
        
        # Chat input
        if prompt := st.chat_input("Ask your question here..."):
            st.markdown("""
            <style>
            /* Dark theme for chat messages */
            .stChatMessage {
                background-color: rgba(30, 34, 40, 0.95) !important;
                border-radius: 10px !important;
                padding: 15px !important;
                margin: 5px 0 !important;
            }
            
            /* Style for user messages */
            .stChatMessage[data-testid="user-message"] {
                background-color: rgba(55, 60, 70, 0.95) !important;
            }
            
            /* Style for assistant messages */
            .stChatMessage[data-testid="assistant-message"] {
                background-color: rgba(40, 45, 55, 0.95) !important;
            }
            
            /* Text color for better visibility */
            .stMarkdown {
                color: #ffffff !important;
            }
            
            /* Input box styling */
            .stTextInput input {
                background-color: rgba(30, 34, 40, 0.95) !important;
                color: white !important;
                border: 1px solid #4a4a4a !important;
            }
            
            /* Sidebar styling */
            .css-1d391kg {
                background-color: rgba(30, 34, 40, 0.95) !important;
            }
            </style>
        """, unsafe_allow_html=True)
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Display assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                sources_placeholder = st.empty()
                
                # Get response with spinner
                with st.spinner("Thinking..."):
                    try:
                        result = st.session_state.rag_pipeline.query(prompt)
                        response = result["answer"]
                        sources = self.format_sources(result["source_documents"])
                        
                        # Update message placeholders
                        message_placeholder.markdown(response)
                        with sources_placeholder.expander("View Sources"):
                            st.markdown(sources)
                        
                        # Save to chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "sources": sources
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing query: {str(e)}")
                        message_placeholder.error("I apologize, but I encountered an error. Please try again.")
    
    # def setup_ui(self):
    #     """Setup the Streamlit UI"""
    #     # Sidebar
    #     with st.sidebar:
    #         st.image("/Users/karolbhandari/Desktop/Customer Care/rag_project/venv/src/src/assets/logo.png", width=200)  # Add your logo
    #         st.title("BYD Nepal AI Assistant")
    #         st.markdown("---")
    #         st.markdown("### About")
    #         st.markdown("""
    #         This AI assistant helps you find information about BYD Nepal's products and services.
            
    #         **Features:**
    #         - Contextual Responses
    #         - Conversation Memory
    #         """)
            # # PDF Upload
            # uploaded_file = st.file_uploader(
            #     "Upload PDF Document",
            #     type=["pdf"],
            #     help="Upload the PDF document you want to query"
            # )
            
            # if uploaded_file:
            #     with st.spinner("Processing document..."):
            #         self.process_uploaded_file(uploaded_file)
            
            # st.markdown("---")
            # st.markdown("### Settings")
            
        #     # Model settings
        #     model = st.selectbox(
        #         "Select Model",
        #         ["gpt-4", "gpt-3.5-turbo"],
        #         index=0
        #     )
            
        #     temperature = st.slider(
        #         "Temperature",
        #         min_value=0.0,
        #         max_value=1.0,
        #         value=0.7,
        #         step=0.1,
        #         help="Controls creativity of responses"
        #     )
            
        #     st.markdown("---")
        #     st.markdown("### About")
        #     st.markdown("""
        #     This AI assistant helps you find information about BYD Nepal's products and services.
            
        #     **Features:**
        #     - PDF Document Analysis
        #     - Contextual Responses
        #     - Conversation Memory
        #     """)
        
        # # Main chat interface
        # st.title("BYD Nepal AI Assistant")
        
        # # Display chat messages
        # for message in st.session_state.messages:
        #     with st.chat_message(message["role"]):
        #         st.markdown(message["content"])
        #         if "sources" in message:
        #             with st.expander("View Sources"):
        #                 st.markdown(message["sources"])
        
        # # Chat input
        # if prompt := st.chat_input("Ask your question here..."):
        #     if not st.session_state.rag_pipeline:
        #         st.error("Please upload a PDF document first.")
        #         return
            
        #     # Add user message
        #     st.session_state.messages.append({"role": "user", "content": prompt})
            
        #     # Display user message
        #     with st.chat_message("user"):
        #         st.markdown(prompt)
            
        #     # Display assistant response
        #     with st.chat_message("assistant"):
        #         message_placeholder = st.empty()
        #         sources_placeholder = st.empty()
                
        #         # Get response with spinner
        #         with st.spinner("Thinking..."):
        #             try:
        #                 result = st.session_state.rag_pipeline.query(prompt)
        #                 response = result["answer"]
        #                 sources = self.format_sources(result["source_documents"])
                        
        #                 # Update message placeholders
        #                 message_placeholder.markdown(response)
        #                 with sources_placeholder.expander("View Sources"):
        #                     st.markdown(sources)
                        
        #                 # Save to chat history
        #                 st.session_state.messages.append({
        #                     "role": "assistant",
        #                     "content": response,
        #                     "sources": sources
        #                 })
                        
        #             except Exception as e:
        #                 logger.error(f"Error processing query: {str(e)}")
        #                 message_placeholder.error("I apologize, but I encountered an error. Please try again.")
    
    def process_uploaded_file(self, uploaded_file):
        """Process uploaded PDF file"""
        try:
            # Save uploaded file temporarily
            temp_path = f"temp_{int(time.time())}.pdf"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Initialize components
            doc_processor = DocumentProcessor()
            embedding_manager = EmbeddingManager()
            
            # Process document
            chunks = doc_processor.process_pdf(temp_path)
            if not chunks:
                st.error("No content could be extracted from the PDF.")
                return
            
            # Create vector store
            vector_store = embedding_manager.create_or_load_vector_store(chunks)
            
            # Initialize RAG pipeline
            st.session_state.rag_pipeline = RAGPipeline(vector_store)
            st.success("Document processed successfully!")
            
            # Cleanup
            os.remove(temp_path)
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            st.error("Error processing the document. Please try again.")
    
    def format_sources(self, source_documents):
        """Format source documents for display"""
        sources_text = ""
        for i, doc in enumerate(source_documents, 1):
            content_preview = doc.page_content[:200] + "..."
            sources_text += f"**Source {i}:**\n\n{content_preview}\n\n---\n\n"
        return sources_text

if __name__ == "__main__":
    st.set_page_config(
        page_title="BYD Nepal AI Assistant",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .stChatMessage {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 0;
        }
        .stMarkdown {
            font-size: 16px;
        }
        .stButton button {
            background-color: #0066cc;
            color: white;
            border-radius: 5px;
        }
        .sidebar .stImage {
            margin: 20px auto;
            display: block;
        }
        </style>
    """, unsafe_allow_html=True)
    
    app = StreamlitRAGApp()