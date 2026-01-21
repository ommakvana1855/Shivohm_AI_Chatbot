from typing import List, Dict, Any
from database.qdrant_client import QdrantDatabase
from database.mongo_client import MongoDatabase
from services.embedding_service import EmbeddingService
from utils.text_processor import TextProcessor
from config.settings import settings


class RetrievalService:
    def __init__(self):
        self.qdrant_db = QdrantDatabase()
        self.mongo_db = MongoDatabase()
        self.embedding_service = EmbeddingService()
        self.text_processor = TextProcessor()
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Add a document to both MongoDB and Qdrant"""
        # Store in MongoDB
        doc_id = self.mongo_db.add_document(content, metadata)
        
        # Chunk the text
        chunks = self.text_processor.chunk_text(content)
        
        # Generate embeddings
        embeddings = self.embedding_service.get_embeddings(chunks)
        
        # Prepare payloads
        payloads = [
            {
                "doc_id": doc_id,
                "chunk_index": i,
                "content": chunk,
                "metadata": metadata or {}
            }
            for i, chunk in enumerate(chunks)
        ]
        
        # Store in Qdrant
        self.qdrant_db.add_vectors(embeddings, payloads)
        
        return doc_id
    
    def retrieve_relevant_context(
        self,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query"""
        top_k = top_k or settings.TOP_K_RESULTS
        
        # Generate query embedding
        query_embedding = self.embedding_service.get_embedding(query)
        
        # Search in Qdrant
        results = self.qdrant_db.search(
            query_vector=query_embedding,
            limit=top_k
        )
        
        return results
    
    def get_context_string(self, results: List[Dict[str, Any]]) -> str:
        """Convert retrieval results to context string"""
        context_parts = []
        for result in results:
            content = result["payload"]["content"]
            context_parts.append(content)
        
        context = "\n\n".join(context_parts)
        
        # Truncate if too long
        return self.text_processor.truncate_to_token_limit(
            context,
            settings.MAX_CONTEXT_LENGTH
        )
