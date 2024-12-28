import os
import logging
from dotenv import load_dotenv
from document_processor import DocumentProcessor
from embedding_manager import EmbeddingManager
from rag_pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGApplication:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.setup_environment()
        
        # Initialize components
        self.doc_processor = DocumentProcessor()
        self.embedding_manager = EmbeddingManager()
        
    def setup_environment(self):
        """Setup environment variables"""
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")

    def initialize_vector_store(self, force_reload: bool = False):
        """Initialize or load vector store"""
        try:
            # Always process the document first
            logger.info("Processing PDF document...")
            chunks = self.doc_processor.process_pdf(self.pdf_path)
            
            if not chunks:
                raise ValueError("No chunks were created from the PDF")
            
            logger.info(f"Successfully created {len(chunks)} chunks")
            
            # Create new vector store
            logger.info("Creating vector store...")
            vector_store = self.embedding_manager.create_or_load_vector_store(chunks)
            
            # Verify vector store
            collection = vector_store._collection
            if collection:
                count = len(collection.get()['ids'])
                logger.info(f"Vector store created with {count} embeddings")
                if count == 0:
                    raise ValueError("Vector store was created but contains no embeddings")
            
            return vector_store
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def run_interactive(self):
        """Run interactive query session"""
        try:
            # Force reload the vector store
            logger.info("Initializing vector store with force reload")
            vector_store = self.initialize_vector_store(force_reload=True)
            
            # Verify vector store content
            collection = vector_store._collection
            if collection:
                count = len(collection.get()['ids'])
                logger.info(f"Vector store size: {count} documents")
                if count == 0:
                    raise ValueError("Vector store is empty. Cannot proceed with queries.")
            
            rag_pipeline = RAGPipeline(vector_store)
            
            print("\nRAG System Ready! Enter your questions (type 'quit' to exit)")
            while True:
                try:
                    question = input("\nQuestion: ").strip()
                    if question.lower() == 'quit':
                        break
                    
                    if not question:
                        continue
                    
                    result = rag_pipeline.query(question)
                    print("\nAnswer:", result["answer"])
                    print("\nSources:")
                    for doc in result["source_documents"]:
                        print(f"\nSource chunk {doc.metadata.get('chunk', 'unknown')}:")
                        print(f"Content preview: {doc.page_content[:200]}...")
                        
                except Exception as e:
                    logger.error(f"Error processing question: {str(e)}")
                    print("An error occurred. Please try again.")
                    
        except Exception as e:
            logger.error(f"Error in run_interactive: {str(e)}")
            raise

def main():
    try:
        # First, clear the existing vector store
        vector_db_path = "data/vector_db"
        if os.path.exists(vector_db_path):
            import shutil
            shutil.rmtree(vector_db_path)
            logger.info("Cleared existing vector store")
        
        # Initialize and run application
        pdf_path = "/Users/karolbhandari/Desktop/Customer Care/website_content/cimex_complete_20241228_202336.pdf"
        
        # Verify PDF exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
        
        logger.info(f"Starting application with PDF: {pdf_path}")
        app = RAGApplication(pdf_path)
        app.run_interactive()
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        print("Application error occurred. Please check the logs.")

if __name__ == "__main__":
    main()