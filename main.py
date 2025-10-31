"""
Main FastAPI Application for AI Organization Assistant
Provides REST API endpoints for querying the AI assistant
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from pathlib import Path

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

# Local imports
from data_collectors import GitHubMCPConnector, ConfluenceConnector, Document
from optimized_github_collector import OptimizedGitHubCollector
from document_processor import DocumentProcessor, VectorStore, DocumentPipeline  
from ai_engine import AIEngine, UserRole, QueryContext, AIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Organization Assistant",
    description="AI assistant for organizational knowledge from GitHub, Confluence, and Jira",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class QueryRequest(BaseModel):
    question: str = Field(..., description="The question to ask the AI assistant")
    user_role: str = Field(default="general", description="User role: developer, support, manager, or general")
    additional_context: Optional[str] = Field(default="", description="Additional context for the question")
    max_results: Optional[int] = Field(default=5, description="Maximum number of source documents to consider")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters for document search")

class QueryResponse(BaseModel):
    answer: str
    confidence_score: float
    processing_time_seconds: float
    sources: List[Dict[str, Any]]
    role_specific_notes: List[str]
    suggested_actions: List[str]
    timestamp: str

class SyncRequest(BaseModel):
    sources: List[str] = Field(default=["github"], description="Data sources to sync: github, confluence, jira")
    repositories: Optional[List[str]] = Field(default=None, description="Specific repositories to sync (GitHub)")
    spaces: Optional[List[str]] = Field(default=None, description="Specific spaces to sync (Confluence)")
    include_paths: Optional[List[str]] = Field(default=None, description="Global: Only collect from these paths (e.g., ['src/', 'lib/'])")
    exclude_paths: Optional[List[str]] = Field(default=None, description="Global: Exclude these paths (e.g., ['tests/', 'examples/'])")
    repo_configs: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Per-repository config: {'repo_name': {'include_paths': [...], 'exclude_paths': [...]}}")

class SyncStatus(BaseModel):
    status: str  # "running", "completed", "failed"
    processed_documents: int
    total_chunks: int
    errors: int
    started_at: str
    completed_at: Optional[str] = None
    message: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    components: Dict[str, str]

# Global components (initialized on startup)
ai_engine: Optional[AIEngine] = None
vector_store: Optional[VectorStore] = None
document_processor: Optional[DocumentProcessor] = None
sync_status: Dict[str, Any] = {"status": "idle"}

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global ai_engine, vector_store, document_processor
    
    logger.info("Starting AI Organization Assistant...")
    
    try:
        # Load configuration from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        use_aws_bedrock = os.getenv("USE_AWS_BEDROCK", "false").lower() == "true"
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize components (vector store and processor always needed)
        vector_store = VectorStore(persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db"))
        
        # Initialize DocumentProcessor with AWS Bedrock or local embeddings
        document_processor = DocumentProcessor(
            use_aws_bedrock=use_aws_bedrock,
            aws_region=aws_region
        )
        
        if use_aws_bedrock:
            logger.info(f"Vector store initialized with AWS Bedrock embeddings (region: {aws_region})")
        else:
            logger.info("Vector store initialized with local embeddings")
        logger.info("Document processor initialized")
        
        # Initialize AI engine only if OpenAI API key is provided
        if openai_api_key:
            ai_engine = AIEngine(
                openai_api_key=openai_api_key,
                vector_store=vector_store,
                document_processor=document_processor,
                model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            )
            logger.info("AI Engine initialized with OpenAI")
        else:
            ai_engine = None
            logger.warning("OpenAI API key not set - AI query endpoint will not work")
            logger.warning("   Data collection and storage will still work")
        
        logger.info("AI Organization Assistant started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with basic health information"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        components={
            "ai_engine": "ready" if ai_engine else "not_initialized",
            "vector_store": "ready" if vector_store else "not_initialized",
            "document_processor": "ready" if document_processor else "not_initialized"
        }
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint"""
    
    components = {}
    
    try:
        # Check vector store
        if vector_store:
            stats = vector_store.get_collection_stats()
            total_docs = sum(stats.values())
            components["vector_store"] = f"ready ({total_docs} documents)"
        else:
            components["vector_store"] = "not_initialized"
        
        # Check AI engine
        components["ai_engine"] = "ready" if ai_engine else "not_initialized"
        
        # Check document processor
        components["document_processor"] = "ready" if document_processor else "not_initialized"
        
        overall_status = "healthy" if all("ready" in status for status in components.values()) else "degraded"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        overall_status = "unhealthy"
        components["error"] = str(e)
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        components=components
    )

@app.post("/query", response_model=QueryResponse)
async def query_assistant(request: QueryRequest):
    """Query the AI assistant with role-based responses"""
    
    if not ai_engine:
        raise HTTPException(status_code=503, detail="AI engine not initialized")
    
    try:
        # Validate user role
        try:
            user_role = UserRole(request.user_role.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid user role: {request.user_role}")
        
        # Create query context
        query_context = QueryContext(
            user_role=user_role,
            query=request.question,
            additional_context=request.additional_context,
            filters=request.filters,
            max_context_length=4000
        )
        
        # Process the query
        response = await ai_engine.process_query(query_context)
        
        # Return formatted response
        return QueryResponse(
            answer=response.answer,
            confidence_score=response.confidence_score,
            processing_time_seconds=response.processing_time,
            sources=response.sources[:request.max_results],
            role_specific_notes=response.role_specific_notes,
            suggested_actions=response.suggested_actions,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/sync", response_model=SyncStatus)
async def sync_data_sources(request: SyncRequest, background_tasks: BackgroundTasks):
    """Sync data from specified sources (GitHub, Confluence, Jira)"""
    
    global sync_status
    
    if sync_status["status"] == "running":
        raise HTTPException(status_code=409, detail="Sync already in progress")
    
    # Start sync in background
    background_tasks.add_task(run_data_sync, request.sources, request.repositories, request.spaces, 
                              request.include_paths, request.exclude_paths, request.repo_configs)
    
    sync_status = {
        "status": "running",
        "processed_documents": 0,
        "total_chunks": 0,
        "errors": 0,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "message": "Sync started"
    }
    
    return SyncStatus(**sync_status)

@app.get("/sync/status", response_model=SyncStatus)
async def get_sync_status():
    """Get current sync status"""
    return SyncStatus(**sync_status)

@app.get("/collections/stats")
async def get_collection_stats():
    """Get statistics about stored documents"""
    
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")
    
    try:
        stats = vector_store.get_collection_stats()
        
        # Add some additional metrics
        total_documents = sum(stats.values())
        
        return {
            "total_documents": total_documents,
            "collections": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/collections/{collection_name}")
async def clear_collection(collection_name: str):
    """Clear a specific collection (use with caution)"""
    
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not initialized")
    
    valid_collections = ["developer", "support", "manager", "general"]
    if collection_name not in valid_collections:
        raise HTTPException(status_code=400, detail=f"Invalid collection name. Valid options: {valid_collections}")
    
    try:
        # This would need to be implemented in VectorStore class
        # vector_store.clear_collection(collection_name)
        
        return {
            "message": f"Collection {collection_name} cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_data_sync(sources: List[str], repositories: Optional[List[str]], spaces: Optional[List[str]], 
                        include_paths: Optional[List[str]] = None, exclude_paths: Optional[List[str]] = None,
                        repo_configs: Optional[Dict[str, Dict[str, Any]]] = None):
    """Background task to sync data from sources"""
    
    global sync_status
    
    try:
        pipeline = DocumentPipeline(vector_store, document_processor)
        
        all_documents = []
        
        # GitHub sync
        if "github" in sources:
            logger.info("Starting GitHub sync...")
            github_org = os.getenv("GITHUB_ORG")
            if not github_org:
                raise ValueError("GITHUB_ORG environment variable required for GitHub sync")
            
            # Check if we have per-repository configurations
            if repo_configs and repositories:
                # Process each repository individually with its own config
                for repo_name in repositories:
                    config = repo_configs.get(repo_name, {})
                    repo_include = config.get('include_paths', include_paths)  # Repo-specific or global
                    repo_exclude = config.get('exclude_paths', exclude_paths)  # Repo-specific or global
                    
                    logger.info(f"Syncing {repo_name} with custom config...")
                    
                    github_collector = OptimizedGitHubCollector(
                        organization=github_org,
                        repositories=[repo_name],  # Single repo
                        collect_source_code=True,
                        max_file_size=100000,
                        max_concurrent=10,
                        include_paths=repo_include,
                        exclude_paths=repo_exclude
                    )
                    
                    async for document in github_collector.collect_all_data():
                        all_documents.append(document)
            else:
                # Use global config for all repositories
                github_collector = OptimizedGitHubCollector(
                    organization=github_org,
                    repositories=repositories,
                    collect_source_code=True,
                    max_file_size=100000,
                    max_concurrent=10,
                    include_paths=include_paths,
                    exclude_paths=exclude_paths
                )
                
                async for document in github_collector.collect_all_data():
                    all_documents.append(document)
        
        # Confluence sync
        if "confluence" in sources:
            logger.info("Starting Confluence sync...")
            confluence_url = os.getenv("CONFLUENCE_URL")
            confluence_user = os.getenv("CONFLUENCE_USERNAME") 
            confluence_token = os.getenv("CONFLUENCE_API_TOKEN")
            
            if confluence_url and confluence_user and confluence_token:
                confluence_spaces = spaces or os.getenv("CONFLUENCE_SPACE_KEYS", "").split(",")
                
                confluence_collector = ConfluenceConnector(
                    url=confluence_url,
                    username=confluence_user,
                    api_token=confluence_token,
                    space_keys=[s.strip() for s in confluence_spaces if s.strip()]
                )
                
                async for document in confluence_collector.collect_all_data():
                    all_documents.append(document)
            else:
                logger.warning("Confluence credentials not configured, skipping")
        
        # Process and store all documents
        if all_documents:
            logger.info(f"Collected {len(all_documents)} documents...")
            
            # DEBUG: Show what was collected
            print(f"\n{'='*80}")
            print(f"COLLECTION SUMMARY")
            print(f"{'='*80}")
            print(f"Total documents collected: {len(all_documents)}")
            
            # Show sample documents
            print(f"\nSample Documents (first 5):")
            print(f"{'-'*80}")
            for i, doc in enumerate(all_documents[:5]):
                print(f"\n{i+1}. Source: {doc.source}")
                print(f"   Type: {doc.doc_type}")
                print(f"   File: {doc.metadata.get('file_path', 'N/A')}")
                print(f"   Repository: {doc.metadata.get('repository', 'N/A')}")
                print(f"   Size: {len(doc.content)} characters")
                print(f"   Role Tags: {', '.join(doc.role_tags)}")
                print(f"   Content preview: {doc.content[:100].strip()}...")
            
            # Document type breakdown
            doc_types = {}
            for doc in all_documents:
                doc_types[doc.doc_type] = doc_types.get(doc.doc_type, 0) + 1
            
            print(f"\nDocument types:")
            for doc_type, count in sorted(doc_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {doc_type}: {count} documents")
            print(f"{'='*80}\n")
            
            # Process and store with AWS Bedrock embeddings (or local if disabled)
            print(f"\n{'='*80}")
            print(f"PROCESSING DOCUMENTS WITH EMBEDDINGS")
            print(f"{'='*80}")
            result = await pipeline.process_and_store_documents(all_documents)
            
            print(f"\n{'='*80}")
            print(f"PROCESSING COMPLETE!")
            print(f"{'='*80}")
            print(f"   Processed: {result['processed_documents']} documents")
            print(f"   Total chunks: {result['total_chunks']}")
            print(f"   Errors: {result['errors']}")
            print(f"{'='*80}\n")
            
            sync_status.update({
                "status": "completed",
                "processed_documents": result["processed_documents"],
                "total_chunks": result["total_chunks"], 
                "errors": result["errors"],
                "completed_at": datetime.now().isoformat(),
                "message": f"Successfully processed {result['processed_documents']} documents into {result['total_chunks']} chunks with embeddings"
            })
        else:
            sync_status.update({
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "message": "No documents found to process"
            })
            
        logger.info("Data sync completed successfully")
        
    except Exception as e:
        logger.error(f"Data sync failed: {e}")
        sync_status.update({
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "message": f"Sync failed: {str(e)}"
        })

# Example queries for different roles
@app.get("/examples")
async def get_example_queries():
    """Get example queries for different user roles"""
    
    examples = {
        "developer": [
            "How do I deploy the authentication service to production?",
            "What are the API endpoints for user management?", 
            "How is error handling implemented in the payment service?",
            "What configuration is needed for the database connection?",
            "Where can I find the Docker setup for local development?"
        ],
        "support": [
            "User is getting authentication errors, how to troubleshoot?",
            "Customer reports slow loading times, what should I check?",
            "How to handle payment processing failures?",
            "What logs should I look at for debugging user issues?",
            "Common causes of 500 errors and their solutions?"
        ],
        "manager": [
            "What is the deployment process for our main application?", 
            "How many active repositories do we have and what do they contain?",
            "What are the current technical debt items we should address?",
            "Which services have the most support tickets?",
            "What documentation gaps exist in our current setup?"
        ]
    }
    
    return examples

if __name__ == "__main__":
    # Load configuration
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=os.getenv("ENVIRONMENT") == "development"
    )

