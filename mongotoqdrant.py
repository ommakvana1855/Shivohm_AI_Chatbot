#!/usr/bin/env python3
"""
Script to migrate data from MongoDB to Qdrant vector database
Uses OpenAI embeddings and loads configuration from .env file
"""

import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
import hashlib
from tqdm import tqdm
from dotenv import load_dotenv
import time


class MongoToQdrantMigrator:
    """Handles migration from MongoDB to Qdrant vector database using OpenAI embeddings"""
    
    def __init__(
        self,
        mongo_uri: str,
        mongo_db: str,
        mongo_collection: str,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        qdrant_api_key: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        openai_api_key: str = None,
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        Initialize connections to MongoDB and Qdrant
        
        Args:
            mongo_uri: MongoDB connection string
            mongo_db: MongoDB database name
            mongo_collection: MongoDB collection name
            qdrant_host: Qdrant host (default: localhost)
            qdrant_port: Qdrant port (default: 6333)
            qdrant_api_key: Qdrant API key (for cloud)
            qdrant_url: Qdrant cloud URL (alternative to host:port)
            openai_api_key: OpenAI API key
            embedding_model: OpenAI embedding model name
        """
        # Connect to MongoDB
        try:
            self.mongo_client = MongoClient(mongo_uri)
            self.mongo_client.admin.command('ping')
            print(f"✓ Connected to MongoDB successfully")
            
            self.mongo_db = self.mongo_client[mongo_db]
            self.mongo_collection = self.mongo_db[mongo_collection]
            doc_count = self.mongo_collection.count_documents({})
            print(f"✓ Using MongoDB collection: {mongo_db}.{mongo_collection} ({doc_count} documents)")
            
        except ConnectionFailure as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            raise
        
        # Connect to Qdrant
        try:
            if qdrant_url:
                self.qdrant_client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key
                )
            else:
                self.qdrant_client = QdrantClient(
                    host=qdrant_host,
                    port=qdrant_port,
                    api_key=qdrant_api_key
                )
            print(f"✓ Connected to Qdrant successfully")
            
        except Exception as e:
            print(f"✗ Failed to connect to Qdrant: {e}")
            raise
        
        # Initialize OpenAI client
        if not openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.embedding_model = embedding_model
        
        # Get vector dimensions by testing with a sample
        print(f"⏳ Initializing OpenAI embedding model: {embedding_model}...")
        test_embedding = self.create_embedding("test")
        self.vector_size = len(test_embedding)
        print(f"✓ OpenAI embedding model ready (dimension: {self.vector_size})")
    
    def generate_id(self, text: str) -> str:
        """
        Generate a unique ID from text using hash
        
        Args:
            text: Text to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.md5(text.encode()).hexdigest()
    
    def create_embedding(self, text: str, retry_count: int = 3) -> List[float]:
        """
        Create embedding vector for text using OpenAI API
        
        Args:
            text: Text to embed
            retry_count: Number of retries on failure
            
        Returns:
            Embedding vector as list of floats
        """
        for attempt in range(retry_count):
            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
            
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⚠ Embedding API error (attempt {attempt + 1}/{retry_count}): {e}")
                    print(f"  Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to create embedding after {retry_count} attempts: {e}")
    
    def prepare_text_for_embedding(self, doc: Dict[str, Any], 
                                   text_fields: List[str] = None) -> str:
        """
        Prepare text from document for embedding
        
        Args:
            doc: MongoDB document
            text_fields: Fields to use for embedding (default: ['title', 'content'])
            
        Returns:
            Combined text for embedding
        """
        if text_fields is None:
            text_fields = ['title', 'content']
        
        text_parts = []
        for field in text_fields:
            if field in doc and doc[field]:
                text_parts.append(str(doc[field]))
        
        return " ".join(text_parts)
    
    def create_collection(self, collection_name: str, recreate: bool = False) -> None:
        """
        Create Qdrant collection
        
        Args:
            collection_name: Name of the collection to create
            recreate: If True, delete existing collection first
        """
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_exists = any(col.name == collection_name for col in collections)
            
            if collection_exists:
                if recreate:
                    print(f"⚠ Deleting existing collection: {collection_name}")
                    self.qdrant_client.delete_collection(collection_name)
                else:
                    print(f"✓ Collection '{collection_name}' already exists")
                    return
            
            # Create collection
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"✓ Created collection: {collection_name}")
            
        except Exception as e:
            print(f"✗ Error creating collection: {e}")
            raise
    
    def migrate(
        self,
        qdrant_collection: str,
        text_fields: List[str] = None,
        batch_size: int = 100,
        recreate_collection: bool = False,
        filter_query: Dict = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Migrate documents from MongoDB to Qdrant
        
        Args:
            qdrant_collection: Name of Qdrant collection
            text_fields: Fields to use for embeddings (default: ['title', 'content'])
            batch_size: Number of documents to process in each batch
            recreate_collection: If True, recreate collection
            filter_query: MongoDB filter query (default: {})
            limit: Maximum number of documents to migrate
            
        Returns:
            Dictionary with migration statistics
        """
        if text_fields is None:
            text_fields = ['title', 'content']
        
        if filter_query is None:
            filter_query = {}
        
        print("\n" + "=" * 60)
        print("Starting Migration: MongoDB → Qdrant")
        print("=" * 60)
        
        # Create collection
        self.create_collection(qdrant_collection, recreate=recreate_collection)
        
        # Count documents
        total_docs = self.mongo_collection.count_documents(filter_query)
        if limit:
            total_docs = min(total_docs, limit)
        
        print(f"\nDocuments to migrate: {total_docs}")
        print(f"Embedding model: {self.embedding_model}")
        print(f"Text fields: {', '.join(text_fields)}")
        print(f"Batch size: {batch_size}")
        print("-" * 60)
        
        if total_docs == 0:
            print("✗ No documents found to migrate")
            return {"total": 0, "successful": 0, "failed": 0}
        
        # Fetch documents
        cursor = self.mongo_collection.find(filter_query)
        if limit:
            cursor = cursor.limit(limit)
        
        successful = 0
        failed = 0
        points_batch = []
        
        # Process documents with progress bar
        with tqdm(total=total_docs, desc="Migrating", unit="doc") as pbar:
            for doc in cursor:
                try:
                    # Prepare text
                    text = self.prepare_text_for_embedding(doc, text_fields)
                    
                    if not text.strip():
                        print(f"\n⚠ Skipping document with empty text: {doc.get('_id')}")
                        failed += 1
                        pbar.update(1)
                        continue
                    
                    # Truncate text if too long (OpenAI has token limits)
                    max_chars = 8000  # Conservative limit
                    if len(text) > max_chars:
                        text = text[:max_chars]
                    
                    # Generate embedding using OpenAI
                    vector = self.create_embedding(text)
                    
                    # Prepare payload (exclude _id, convert to JSON-serializable)
                    payload = {}
                    for key, value in doc.items():
                        if key != '_id':
                            # Convert ObjectId and other non-serializable types to string
                            if hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                payload[key] = str(value)
                            else:
                                payload[key] = value
                    
                    # Add original MongoDB ID to payload
                    payload['mongo_id'] = str(doc['_id'])
                    
                    # Generate point ID
                    point_id = self.generate_id(str(doc['_id']))
                    
                    # Create point
                    point = PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                    
                    points_batch.append(point)
                    
                    # Upload batch
                    if len(points_batch) >= batch_size:
                        self.qdrant_client.upsert(
                            collection_name=qdrant_collection,
                            points=points_batch
                        )
                        successful += len(points_batch)
                        points_batch = []
                    
                    pbar.update(1)
                    
                except Exception as e:
                    print(f"\n✗ Error processing document {doc.get('_id')}: {e}")
                    failed += 1
                    pbar.update(1)
            
            # Upload remaining points
            if points_batch:
                try:
                    self.qdrant_client.upsert(
                        collection_name=qdrant_collection,
                        points=points_batch
                    )
                    successful += len(points_batch)
                except Exception as e:
                    print(f"\n✗ Error uploading final batch: {e}")
                    failed += len(points_batch)
        
        print("-" * 60)
        print(f"✓ Migration completed!")
        print(f"  Total: {total_docs}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        
        return {
            "total": total_docs,
            "successful": successful,
            "failed": failed
        }
    
    def verify_migration(self, qdrant_collection: str) -> None:
        """
        Verify the migration by checking collection info
        
        Args:
            qdrant_collection: Name of Qdrant collection
        """
        try:
            collection_info = self.qdrant_client.get_collection(qdrant_collection)
            print("\n" + "=" * 60)
            print("Collection Information")
            print("=" * 60)
            print(f"Collection name: {qdrant_collection}")
            print(f"Vector size: {collection_info.config.params.vectors.size}")
            print(f"Distance metric: {collection_info.config.params.vectors.distance}")
            print(f"Points count: {collection_info.points_count}")
            print("=" * 60)
            
        except Exception as e:
            print(f"✗ Error verifying migration: {e}")
    
    def close(self):
        """Close connections"""
        self.mongo_client.close()
        print("\n✓ Connections closed")


def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration from .env file
    
    Returns:
        Dictionary with configuration values
    """
    # Load .env file
    load_dotenv()
    
    # Required configurations
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    # MongoDB configuration
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    mongo_db = os.getenv('MONGODB_DB_NAME', 'Shivohm_Website_database')
    mongo_collection = os.getenv('MONGODB_COLLECTION_NAME', 'Crawler_data')
    
    # Qdrant configuration
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    qdrant_collection = os.getenv('QDRANT_COLLECTION_NAME', 'Shivohm_chatbot_knowledge')
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    
    # Model configuration
    embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    
    # Migration settings
    batch_size = int(os.getenv('BATCH_SIZE', '100'))
    text_fields_str = os.getenv('TEXT_FIELDS', 'title,content')
    text_fields = [f.strip() for f in text_fields_str.split(',')]
    recreate_collection = os.getenv('RECREATE_COLLECTION', 'false').lower() == 'true'
    
    return {
        'openai_api_key': openai_api_key,
        'mongo_uri': mongo_uri,
        'mongo_db': mongo_db,
        'mongo_collection': mongo_collection,
        'qdrant_host': qdrant_host,
        'qdrant_port': qdrant_port,
        'qdrant_collection': qdrant_collection,
        'qdrant_url': qdrant_url,
        'qdrant_api_key': qdrant_api_key,
        'embedding_model': embedding_model,
        'batch_size': batch_size,
        'text_fields': text_fields,
        'recreate_collection': recreate_collection
    }


def main():
    """Main function to run the migration"""
    
    print("=" * 60)
    print("MongoDB to Qdrant Vector Database Migration")
    print("Using OpenAI Embeddings")
    print("=" * 60)
    
    try:
        # Load configuration from .env
        print("\n⏳ Loading configuration from .env file...")
        config = load_config_from_env()
        print("✓ Configuration loaded successfully\n")
        
        # Display configuration (mask API key)
        print("Configuration:")
        print(f"  MongoDB: {config['mongo_db']}.{config['mongo_collection']}")
        print(f"  Qdrant: {config['qdrant_collection']}")
        print(f"  Embedding Model: {config['embedding_model']}")
        print(f"  OpenAI API Key: {'*' * 20}{config['openai_api_key'][-4:]}")
        print()
        
        # Create migrator instance
        migrator = MongoToQdrantMigrator(
            mongo_uri=config['mongo_uri'],
            mongo_db=config['mongo_db'],
            mongo_collection=config['mongo_collection'],
            qdrant_host=config['qdrant_host'],
            qdrant_port=config['qdrant_port'],
            qdrant_api_key=config['qdrant_api_key'],
            qdrant_url=config['qdrant_url'],
            openai_api_key=config['openai_api_key'],
            embedding_model=config['embedding_model']
        )
        
        # Run migration
        stats = migrator.migrate(
            qdrant_collection=config['qdrant_collection'],
            text_fields=config['text_fields'],
            batch_size=config['batch_size'],
            recreate_collection=config['recreate_collection']
        )
        
        # Verify migration
        migrator.verify_migration(config['qdrant_collection'])
        
        # Close connections
        migrator.close()
        
        # Display summary
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"✓ Successfully migrated {stats['successful']} documents")
        if stats['failed'] > 0:
            print(f"⚠ Failed to migrate {stats['failed']} documents")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())