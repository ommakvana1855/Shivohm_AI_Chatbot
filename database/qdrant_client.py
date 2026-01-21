from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
from config.settings import settings
import uuid


class QdrantDatabase:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            print(f"Created Qdrant collection: {self.collection_name}")
    
    def add_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]]
    ) -> List[str]:
        """Add vectors with metadata to Qdrant"""
        ids = [str(uuid.uuid4()) for _ in vectors]
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        return ids
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,  # Changed from query_vector to query
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results.points  # Access points attribute
        ]
    
    def delete_by_id(self, point_id: str):
        """Delete a vector by ID"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[point_id]
        )