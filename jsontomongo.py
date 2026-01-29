#!/usr/bin/env python3
"""
Script to upload JSON files from a folder to MongoDB
"""

import json
import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, BulkWriteError
from typing import List, Dict, Any


class JSONToMongoUploader:
    """Handles uploading JSON files to MongoDB"""
    
    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string (e.g., 'mongodb://localhost:27017/')
            database_name: Name of the database
            collection_name: Name of the collection
        """
        try:
            self.client = MongoClient(connection_string)
            # Test connection
            self.client.admin.command('ping')
            print(f"✓ Connected to MongoDB successfully")
            
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            print(f"✓ Using database: {database_name}, collection: {collection_name}")
            
        except ConnectionFailure as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            raise
    
    def load_json_file(self, file_path: Path) -> Dict[Any, Any]:
        """
        Load a single JSON file
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Parsed JSON data as dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON file {file_path}: {e}")
            return None
        except Exception as e:
            print(f"✗ Error reading file {file_path}: {e}")
            return None
    
    def upload_file(self, file_path: Path) -> bool:
        """
        Upload a single JSON file to MongoDB
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            True if successful, False otherwise
        """
        data = self.load_json_file(file_path)
        
        if data is None:
            return False
        
        try:
            # Insert the document
            result = self.collection.insert_one(data)
            print(f"✓ Uploaded {file_path.name} - Document ID: {result.inserted_id}")
            return True
        except Exception as e:
            print(f"✗ Error uploading {file_path.name}: {e}")
            return False
    
    def upload_files_bulk(self, file_paths: List[Path]) -> tuple:
        """
        Upload multiple JSON files in bulk operation
        
        Args:
            file_paths: List of paths to JSON files
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        documents = []
        failed_files = []
        
        # Load all files first
        for file_path in file_paths:
            data = self.load_json_file(file_path)
            if data is not None:
                documents.append(data)
            else:
                failed_files.append(file_path.name)
        
        if not documents:
            print("✗ No valid documents to upload")
            return 0, len(file_paths)
        
        try:
            # Bulk insert
            result = self.collection.insert_many(documents, ordered=False)
            successful_count = len(result.inserted_ids)
            print(f"✓ Bulk upload successful: {successful_count} documents inserted")
            
            if failed_files:
                print(f"✗ Failed to load {len(failed_files)} files: {', '.join(failed_files)}")
            
            return successful_count, len(failed_files)
            
        except BulkWriteError as e:
            print(f"✗ Bulk write error: {e.details}")
            successful_count = e.details.get('nInserted', 0)
            failed_count = len(documents) - successful_count + len(failed_files)
            return successful_count, failed_count
        except Exception as e:
            print(f"✗ Error during bulk upload: {e}")
            return 0, len(file_paths)
    
    def upload_from_folder(self, folder_path: str, bulk_upload: bool = True, 
                          file_pattern: str = "*.json") -> None:
        """
        Upload all JSON files from a folder
        
        Args:
            folder_path: Path to the folder containing JSON files
            bulk_upload: If True, use bulk upload; if False, upload one by one
            file_pattern: Pattern to match JSON files (default: "*.json")
        """
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"✗ Folder does not exist: {folder_path}")
            return
        
        if not folder.is_dir():
            print(f"✗ Path is not a folder: {folder_path}")
            return
        
        # Find all JSON files
        json_files = list(folder.glob(file_pattern))
        
        if not json_files:
            print(f"✗ No JSON files found in {folder_path}")
            return
        
        print(f"\nFound {len(json_files)} JSON file(s) in {folder_path}")
        print("-" * 60)
        
        if bulk_upload:
            successful, failed = self.upload_files_bulk(json_files)
            print("-" * 60)
            print(f"Summary: {successful} successful, {failed} failed")
        else:
            successful = 0
            failed = 0
            for file_path in json_files:
                if self.upload_file(file_path):
                    successful += 1
                else:
                    failed += 1
            
            print("-" * 60)
            print(f"Summary: {successful} successful, {failed} failed")
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        print("\n✓ MongoDB connection closed")


def main():
    """Main function to run the script"""
    
    # Configuration
    MONGODB_URI = "mongodb://localhost:27017/"  # Change this to your MongoDB URI
    DATABASE_NAME = "Shivohm_Website_database"                 # Change this to your database name
    COLLECTION_NAME = "Crawler_data"                    # Change this to your collection name
    JSON_FOLDER = "shivohm_Website_data"                 # Change this to your folder path
    USE_BULK_UPLOAD = True                       # Set to False for one-by-one upload
    
    print("=" * 60)
    print("JSON to MongoDB Uploader")
    print("=" * 60)
    
    try:
        # Create uploader instance
        uploader = JSONToMongoUploader(
            connection_string=MONGODB_URI,
            database_name=DATABASE_NAME,
            collection_name=COLLECTION_NAME
        )
        
        # Upload files from folder
        uploader.upload_from_folder(
            folder_path=JSON_FOLDER,
            bulk_upload=USE_BULK_UPLOAD
        )
                # Close connection
        uploader.close()

        
    except Exception as e:
        print(f"\n✗ An error occurred: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())