import logging
from typing import List
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
import fitz
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):  # Smaller chunks for better retrieval
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

    def clean_text(self, text: str) -> str:
        """Clean the text content"""
        # Remove special characters and normalize spaces
        text = re.sub(r'[^\w\s.,!?-]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ')
        return text.strip()

    def process_pdf(self, pdf_path: str) -> List[Document]:
        """Process PDF document and split into chunks"""
        try:
            logger.info(f"Loading PDF from {pdf_path}")
            
            # Read PDF directly first
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                cleaned_text = self.clean_text(text)
                if cleaned_text:
                    full_text += cleaned_text + " "
                logger.info(f"Processed page {page_num + 1}, length: {len(cleaned_text)}")
            
            # Split into chunks
            chunks = self.text_splitter.create_documents(
                texts=[full_text],
                metadatas=[{"source": pdf_path}]
            )
            
            logger.info(f"Created {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk"] = i
                logger.info(f"Chunk {i}: {len(chunk.page_content)} chars")
                logger.info(f"Preview: {chunk.page_content[:100]}...")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise