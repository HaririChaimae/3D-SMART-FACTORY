#!/usr/bin/env python3
"""
LlamaIndex RAG Integration with Gemini API
==========================================

This module provides LlamaIndex-based RAG functionality using Gemini API
as the LLM, replacing the FAISS + SentenceTransformers implementation.
"""

import os
import sys
from typing import List, Optional

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
    from llama_index.llms.gemini import Gemini
    from llama_index.embeddings.gemini import GeminiEmbedding
    from llama_index.core.node_parser import SimpleNodeParser
    from llama_index.core.storage import StorageContext
    from llama_index.core.indices import load_index_from_storage

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    print("LlamaIndex not available. Install with: pip install llama-index llama-index-llms-gemini")

import logging
logger = logging.getLogger(__name__)

class LlamaIndexRAG:
    """LlamaIndex-based RAG system using Gemini API"""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "models/gemini-2.0-flash"):
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex not installed. Install with: pip install llama-index llama-index-llms-gemini")

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found. Set it as environment variable or pass to constructor.")

        # Configure Gemini LLM
        self.llm = Gemini(
            model_name=model_name,
            api_key=self.api_key,
            temperature=0.0,
            max_tokens=1024
        )

        # Configure embedding model
        self.embed_model = GeminiEmbedding(
            model_name="models/embedding-001",
            api_key=self.api_key
        )

        # Configure LlamaIndex settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.node_parser = SimpleNodeParser.from_defaults(chunk_size=512, chunk_overlap=50)

        self.index = None
        self.storage_dir = "./llamaindex_storage"

    def build_index_from_directory(self, data_dir: str = "data_test") -> None:
        """Build vector index from PDF files in directory"""
        if not os.path.exists(data_dir):
            logger.warning(f"Data directory {data_dir} not found")
            return

        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            logger.warning(f"No PDF files found in {data_dir}")
            return

        logger.info(f"Building LlamaIndex from {len(pdf_files)} PDF files...")

        try:
            # Load documents
            documents = SimpleDirectoryReader(data_dir).load_data()

            # Create index
            self.index = VectorStoreIndex.from_documents(
                documents,
                show_progress=True
            )

            # Persist index
            self.index.storage_context.persist(persist_dir=self.storage_dir)
            logger.info(f"LlamaIndex built and saved to {self.storage_dir}")

        except Exception as e:
            logger.error(f"Error building LlamaIndex: {e}")
            raise

    def load_index(self) -> bool:
        """Load existing index from storage"""
        if not os.path.exists(self.storage_dir):
            return False

        try:
            storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
            self.index = load_index_from_storage(storage_context)
            logger.info("LlamaIndex loaded from storage")
            return True
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False

    def query(self, question: str, top_k: int = 3) -> str:
        """Query the index with a question"""
        if not self.index:
            if not self.load_index():
                return "Index not available. Please build the index first."

        try:
            # Create query engine
            query_engine = self.index.as_query_engine(
                similarity_top_k=top_k,
                response_mode="tree_summarize"
            )

            # Query
            response = query_engine.query(question)
            return str(response)

        except Exception as e:
            logger.error(f"Error querying index: {e}")
            return f"Error: {e}"

def build_llamaindex_store(pdf_files_info=None):
    """Build LlamaIndex store (replacement for build_vector_store)"""
    try:
        rag = LlamaIndexRAG()
        rag.build_index_from_directory("data_test")
        return rag.index, "LlamaIndex store built successfully"
    except Exception as e:
        logger.error(f"Error building LlamaIndex store: {e}")
        return None, str(e)

def search_llamaindex_knowledge(query, index, top_k=2):
    """Search using LlamaIndex (replacement for search_knowledge)"""
    if not isinstance(index, LlamaIndexRAG):
        return []

    try:
        return [index.query(query, top_k=top_k)]
    except Exception as e:
        logger.error(f"Error searching LlamaIndex: {e}")
        return []

def generate_llamaindex_answer(question, index, texts=None, max_context_length=1500):
    """Generate answer using LlamaIndex (replacement for generate_answer_for_question)"""
    if not isinstance(index, LlamaIndexRAG):
        return "LlamaIndex not available"

    try:
        return index.query(question)
    except Exception as e:
        logger.error(f"Error generating answer with LlamaIndex: {e}")
        return f"Error: {e}"

# Example usage
if __name__ == "__main__":
    if LLAMAINDEX_AVAILABLE:
        print("LlamaIndex with Gemini integration available!")

        # Example usage
        rag = LlamaIndexRAG()
        rag.build_index_from_directory("data_test")

        # Test query
        answer = rag.query("What is the sum of two numbers?")
        print(f"Answer: {answer}")
    else:
        print("LlamaIndex not installed. Install with: pip install llama-index llama-index-llms-gemini")