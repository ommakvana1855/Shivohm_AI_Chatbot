from pymongo import MongoClient
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.settings import settings
import uuid


class MongoDatabase:
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DB_NAME]
        self.documents_collection = self.db["documents"]
        self.sessions_collection = self.db["chat_sessions"]
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        self.documents_collection.create_index("created_at")
        self.sessions_collection.create_index("session_id", unique=True)
        self.sessions_collection.create_index("updated_at")
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Add a document to MongoDB"""
        doc_id = str(uuid.uuid4())
        document = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        self.documents_collection.insert_one(document)
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID"""
        return self.documents_collection.find_one({"id": doc_id}, {"_id": 0})
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Retrieve all documents"""
        return list(self.documents_collection.find({}, {"_id": 0}))
    
    def delete_document(self, doc_id: str):
        """Delete a document"""
        self.documents_collection.delete_one({"id": doc_id})
    
    def create_session(self, session_id: str) -> str:
        """Create a new chat session"""
        session = {
            "session_id": session_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        self.sessions_collection.insert_one(session)
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to a session"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        self.sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a chat session"""
        return self.sessions_collection.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
    
    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from a session"""
        session = self.get_session(session_id)
        if session:
            return session.get("messages", [])[-limit:]
        return []