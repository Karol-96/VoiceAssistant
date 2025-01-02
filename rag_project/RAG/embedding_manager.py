import os
import logging
from typing import List
from langchain_core.documents import Document  
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self, persist_directory: str = "data/vector_db"):
        self.persist_directory = persist_directory
        # Updated OpenAIEmbeddings initialization
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model="text-embedding-ada-002"  # Explicitly specify the model
        )
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)

    def create_or_load_vector_store(self, documents: List[Document] = None):
        """Create new vector store or load existing one"""
        try:
            if documents:
                logger.info(f"Creating new vector store with {len(documents)} documents")
                vectordb = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory,
                    collection_metadata={"hnsw:space": "cosine"}
                )
                vectordb.persist()
                
                # Verify storage
                collection = vectordb._collection
                if collection:
                    count = len(collection.get()['ids'])
                    logger.info(f"Vector store created with {count} embeddings")
                
                return vectordb
            else:
                if not os.path.exists(self.persist_directory):
                    logger.warning("No existing vector store found")
                    return None
                    
                logger.info("Loading existing vector store")
                vectordb = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
                
                # Verify the vector store has content
                collection = vectordb._collection
                if collection and len(collection.get()['ids']) > 0:
                    logger.info(f"Loaded vector store with {len(collection.get()['ids'])} embeddings")
                    return vectordb
                else:
                    logger.warning("Vector store exists but is empty")
                    return None
                    
        except Exception as e:
            logger.error(f"Error with vector store: {str(e)}")
            raise