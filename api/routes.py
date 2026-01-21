from fastapi import FastAPI, HTTPException, UploadFile, File
from models.schemas import QueryRequest, QueryResponse, Document
from services.chat_service import ChatService
from services.retrieval_service import RetrievalService
from docx import Document as DocxDocument
import PyPDF2
import io

app = FastAPI(title="RAG Chatbot API")

chat_service = ChatService()
retrieval_service = RetrievalService()


@app.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Chat endpoint with RAG"""
    try:
        result = chat_service.chat(
            query=request.query,
            session_id=request.session_id,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def add_document(document: Document):
    """Add a document to the knowledge base"""
    try:
        doc_id = retrieval_service.add_document(
            content=document.content,
            metadata=document.metadata
        )
        return {"doc_id": doc_id, "message": "Document added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = None
):
    """Upload a Word or PDF file to the knowledge base"""
    try:
        # Read file content
        content_bytes = await file.read()
        
        # Extract text based on file type
        if file.filename.endswith('.docx'):
            doc = DocxDocument(io.BytesIO(content_bytes))
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        elif file.filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        
        elif file.filename.endswith('.txt'):
            content = content_bytes.decode('utf-8')
        
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Use .docx, .pdf, or .txt"
            )
        
        # Parse metadata if provided
        import json
        meta = json.loads(metadata) if metadata else {}
        meta["filename"] = file.filename
        meta["file_type"] = file.filename.split('.')[-1]
        
        # Add to knowledge base
        doc_id = retrieval_service.add_document(content=content, metadata=meta)
        
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "message": "File uploaded and processed successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}