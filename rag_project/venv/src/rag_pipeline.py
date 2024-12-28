import logging
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate  # Added import
from langchain_core.prompts import PromptTemplate  # Alternative import if above doesn't work

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, vector_store, model_name: str = "gpt-4", temperature: float = 0.7):
        self.vector_store = vector_store
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            output_key="answer",
            return_messages=True
        )
        self.qa_chain = self._setup_chain()

    def _setup_chain(self):
        """Setup the RAG chain with conversation memory"""
        try:
            custom_prompt = PromptTemplate(
                template="""You are BYD Nepal's AI Assistant, knowledgeable about all BYD vehicles and services in Nepal. 
                Use the following information to provide natural, confident responses. Don't mention the context or that you're looking up information.
                If you're not sure about something, simply say you'll need to check with the team for the most up-to-date information.

                Context: {context}
                Question: {question}

                Remember to be conversational and enthusiastic about BYD vehicles while maintaining accuracy.""",
                input_variables=["context", "question"]
            )

            return ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vector_store.as_retriever(
                    search_type="mmr",
                    search_kwargs={
                        "k": 8,
                        "fetch_k": 20,
                        "lambda_mult": 0.7
                    }
                ),
                memory=self.memory,
                return_source_documents=True,
                verbose=True,
                combine_docs_chain_kwargs={
                    "prompt": custom_prompt,
                    "document_separator": "\n\n"
                }
            
            )
        except Exception as e:
            logger.error(f"Error setting up RAG chain: {str(e)}")
            raise

    # def _setup_chain(self):
    #     """Setup the RAG chain with conversation memory"""
    #     try:
    #         custom_prompt = PromptTemplate(
    #             template="""You are a helpful assistant for BYD Nepal. Use the following pieces of context to answer the user's question accurately and concisely.
    #             If you don't know the answer based on the context provided, just say "I don't have enough information to answer that question."
                
    #             Context: {context}
                
    #             Question: {question}
                
    #             Please provide a detailed answer based on the context above. If you mention any specific information, make sure it comes directly from the context:""",
    #             input_variables=["context", "question"]
    #         )

    #         return ConversationalRetrievalChain.from_llm(
    #             llm=self.llm,
    #             retriever=self.vector_store.as_retriever(
    #                 search_type="mmr",  # Changed to MMR for better diversity
    #                 search_kwargs={
    #                     "k": 8,  # Increased number of documents
    #                     "fetch_k": 20,  # Fetch more documents initially
    #                     "lambda_mult": 0.7  # Diversity factor
    #                 }
    #             ),
    #             memory=self.memory,
    #             return_source_documents=True,
    #             verbose=True,
    #             combine_docs_chain_kwargs={
    #                 "prompt": custom_prompt,
    #                 "document_separator": "\n\n"
    #             }
    #         )
    #     except Exception as e:
    #         logger.error(f"Error setting up RAG chain: {str(e)}")
    #         raise

    def query(self, question: str) -> dict:
        """Process a question through the RAG pipeline"""
        try:
            logger.info(f"Processing question: {question}")
            result = self.qa_chain.invoke({"question": question})
            return result
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise