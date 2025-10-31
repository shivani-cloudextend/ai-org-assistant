"""
Document Processing Pipeline for AI Organization Assistant
Handles chunking, embedding, and storage of collected documents
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import hashlib
import json
from datetime import datetime
import os

# Third-party imports
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document as LangchainDocument
import tiktoken

# AWS imports (optional - only if using Bedrock)
try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.warning("boto3 not installed - AWS Bedrock will not be available")

from data_collectors import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedChunk:
    """Represents a processed document chunk with embedding"""
    id: str
    content: str
    embedding: List[float]
    source_document_id: str
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any]

class DocumentProcessor:
    """Processes documents into chunks and generates embeddings"""
    
    def __init__(self, 
                 embedding_model: str = "BAAI/bge-large-en-v1.5",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 use_aws_bedrock: bool = False,
                 aws_region: str = "us-east-1"):
        
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_aws_bedrock = use_aws_bedrock
        self.aws_region = aws_region
        
        # Initialize embedder based on configuration
        if use_aws_bedrock:
            if not AWS_AVAILABLE:
                raise ImportError("boto3 is required for AWS Bedrock. Install with: pip install boto3")
            
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region
            )
            self.bedrock_model_id = "amazon.titan-embed-text-v1"
            self.embedder = None  # Not using local embedder
            print(f"Initialized AWS Bedrock embeddings in region {aws_region}")
        else:
            self.embedder = SentenceTransformer(embedding_model)
            self.bedrock_runtime = None
            print(f"Initialized local embeddings with {embedding_model}")
        
        # Initialize text splitters for different content types
        self.text_splitters = {
            'markdown': RecursiveCharacterTextSplitter.from_language(
                language=Language.MARKDOWN,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            ),
            'python': RecursiveCharacterTextSplitter.from_language(
                language=Language.PYTHON,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            ),
            'javascript': RecursiveCharacterTextSplitter.from_language(
                language=Language.JS,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            ),
            'generic': RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
        }
        
        # Token counter for content optimization
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    async def process_document(self, document: Document) -> List[ProcessedChunk]:
        """Process a single document into chunks with embeddings"""
        
        try:
            # Generate unique document ID
            doc_id = self.generate_document_id(document)
            
            # Clean and preprocess content
            cleaned_content = self.clean_content(document.content)
            
            # Skip if content is too short or empty
            if len(cleaned_content.strip()) < 50:
                logger.debug(f"Skipping document with insufficient content: {doc_id}")
                return []
            
            # Choose appropriate text splitter
            splitter = self.choose_text_splitter(document)
            
            # Split document into chunks
            chunks = splitter.split_text(cleaned_content)
            
            if not chunks:
                logger.debug(f"No chunks generated for document: {doc_id}")
                return []
            
            # Generate embeddings for all chunks
            print(f"Generating embeddings for {len(chunks)} chunks from {doc_id}")
            embeddings = await self._generate_embeddings(chunks)
            print(f"Generated {len(embeddings)} embeddings")
            
            # Create processed chunks
            processed_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                
                chunk_id = f"{doc_id}_chunk_{i}"
                
                # Calculate token count for this chunk
                token_count = len(self.tokenizer.encode(chunk))
                
                processed_chunk = ProcessedChunk(
                    id=chunk_id,
                    content=chunk,
                    embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                    source_document_id=doc_id,
                    chunk_index=i,
                    total_chunks=len(chunks),
                    metadata={
                        # Original document metadata
                        **document.metadata,
                        
                        # Document-level info
                        'source': document.source,
                        'doc_type': document.doc_type,
                        'role_tags': document.role_tags,
                        'created_at': document.created_at.isoformat() if document.created_at else None,
                        'updated_at': document.updated_at.isoformat() if document.updated_at else None,
                        
                        # Chunk-level info
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'token_count': token_count,
                        'char_count': len(chunk),
                        'processing_timestamp': datetime.now().isoformat(),
                        
                        # Content classification
                        'content_type': self.classify_content_type(chunk, document.doc_type),
                        'complexity_score': self.calculate_complexity_score(chunk),
                        'has_code': self.contains_code(chunk),
                        'has_urls': self.contains_urls(chunk),
                        
                        # Search optimization
                        'keywords': self.extract_keywords(chunk),
                        'summary': self.generate_chunk_summary(chunk)
                    }
                )
                
                processed_chunks.append(processed_chunk)
            
            logger.info(f"Successfully processed document {doc_id} into {len(processed_chunks)} chunks")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return []
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using either AWS Bedrock or local model"""
        if self.use_aws_bedrock:
            print(f"Using AWS Bedrock to generate {len(texts)} embeddings")
            return await self._generate_bedrock_embeddings(texts)
        else:
            print(f"Using local model to generate {len(texts)} embeddings")
            return self._generate_local_embeddings(texts)
    
    def _generate_local_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local SentenceTransformer model"""
        embeddings = self.embedder.encode(texts, convert_to_tensor=False)
        return [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings]
    
    async def _generate_bedrock_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using AWS Bedrock"""
        embeddings = []
        print(f"Calling AWS Bedrock API for {len(texts)} texts...")
        
        for idx, text in enumerate(texts):
            try:
                # Prepare request for Bedrock
                request_body = json.dumps({"inputText": text})
                
                logger.debug(f"   Bedrock request {idx+1}/{len(texts)} - text length: {len(text)}")
                
                # Call Bedrock API synchronously (boto3 doesn't support async natively)
                response = await asyncio.to_thread(
                    self.bedrock_runtime.invoke_model,
                    modelId=self.bedrock_model_id,
                    body=request_body,
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                embedding = response_body.get('embedding', [])
                embeddings.append(embedding)
                
                if (idx + 1) % 10 == 0 or (idx + 1) == len(texts):
                    msg = f"   Processed {idx+1}/{len(texts)} embeddings via Bedrock"
                    logger.info(msg)
                    print(msg)
                
            except Exception as e:
                error_msg = f"Error generating Bedrock embedding for text {idx+1}: {e}"
                logger.error(error_msg)
                print(error_msg)
                # Return a zero vector as fallback
                embeddings.append([0.0] * 1536)  # Titan embed dimension
        
        print(f"Completed {len(embeddings)} Bedrock embeddings")
        return embeddings
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a single embedding (used for queries)"""
        embeddings = await self._generate_embeddings([text])
        return embeddings[0]
    
    def generate_document_id(self, document: Document) -> str:
        """Generate a unique, deterministic ID for a document"""
        
        # Create a hash based on source, metadata, and content
        content_for_hash = f"{document.source}_{document.doc_type}"
        
        if document.source == 'github':
            content_for_hash += f"_{document.metadata.get('repository')}_{document.metadata.get('file_path')}"
        elif document.source == 'confluence':
            content_for_hash += f"_{document.metadata.get('page_id')}"
        elif document.source == 'jira':
            content_for_hash += f"_{document.metadata.get('issue_key')}"
        
        # Add content hash to ensure uniqueness
        content_hash = hashlib.md5(document.content.encode('utf-8')).hexdigest()[:8]
        content_for_hash += f"_{content_hash}"
        
        return hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()[:16]
    
    def clean_content(self, content: str) -> str:
        """Clean and normalize document content"""
        
        # Remove excessive whitespace
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Skip empty lines that are more than 2 consecutive
            if not line and len(cleaned_lines) > 0 and not cleaned_lines[-1]:
                continue
            
            cleaned_lines.append(line)
        
        # Join lines and normalize spacing
        cleaned = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        import re
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def choose_text_splitter(self, document: Document) -> RecursiveCharacterTextSplitter:
        """Choose appropriate text splitter based on document content"""
        
        # Check file extension or content type
        file_path = document.metadata.get('file_path', '').lower()
        
        if file_path.endswith(('.md', '.markdown')) or document.doc_type == 'documentation':
            return self.text_splitters['markdown']
        elif file_path.endswith(('.py', '.pyw')):
            return self.text_splitters['python']
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return self.text_splitters['javascript']
        elif document.doc_type == 'code':
            # Try to detect language from content
            if 'def ' in document.content or 'import ' in document.content:
                return self.text_splitters['python']
            elif 'function ' in document.content or 'const ' in document.content:
                return self.text_splitters['javascript']
        
        return self.text_splitters['generic']
    
    def classify_content_type(self, content: str, doc_type: str) -> str:
        """Classify the type of content in a chunk"""
        
        content_lower = content.lower()
        
        # Code patterns
        if any(pattern in content for pattern in ['```', 'function', 'class ', 'def ', 'import ', 'const ', 'var ']):
            return 'code_snippet'
        
        # Configuration patterns
        if any(pattern in content_lower for pattern in ['config', 'settings', 'environment', 'env']):
            return 'configuration'
        
        # API documentation
        if any(pattern in content_lower for pattern in ['api', 'endpoint', 'request', 'response', 'curl']):
            return 'api_documentation'
        
        # Troubleshooting content
        if any(pattern in content_lower for pattern in ['error', 'troubleshoot', 'problem', 'solution', 'fix']):
            return 'troubleshooting'
        
        # Installation/setup
        if any(pattern in content_lower for pattern in ['install', 'setup', 'deploy', 'build', 'run']):
            return 'setup_instructions'
        
        return doc_type or 'general'
    
    def calculate_complexity_score(self, content: str) -> float:
        """Calculate complexity score for content (0.0 to 1.0)"""
        
        score = 0.0
        
        # Technical terms increase complexity
        technical_terms = ['api', 'configuration', 'deployment', 'architecture', 'algorithm']
        tech_count = sum(1 for term in technical_terms if term in content.lower())
        score += min(tech_count * 0.1, 0.3)
        
        # Code increases complexity
        if self.contains_code(content):
            score += 0.3
        
        # Length increases complexity
        if len(content) > 800:
            score += 0.2
        
        # Multiple sentences/paragraphs
        sentence_count = len([s for s in content.split('.') if s.strip()])
        if sentence_count > 5:
            score += 0.2
        
        return min(score, 1.0)
    
    def contains_code(self, content: str) -> bool:
        """Check if content contains code snippets"""
        code_indicators = ['```', '    ', '\t', 'function(', 'def ', 'class ', 'import ', 'from ']
        return any(indicator in content for indicator in code_indicators)
    
    def contains_urls(self, content: str) -> bool:
        """Check if content contains URLs"""
        import re
        url_pattern = r'https?://[^\s]+'
        return bool(re.search(url_pattern, content))
    
    def extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from content"""
        
        import re
        
        # Common technical keywords to look for
        technical_keywords = [
            'api', 'sdk', 'auth', 'authentication', 'authorization', 'config', 'configuration',
            'deploy', 'deployment', 'build', 'test', 'debug', 'error', 'exception',
            'database', 'cache', 'queue', 'service', 'microservice', 'container', 'docker',
            'kubernetes', 'aws', 'azure', 'gcp', 'cloud', 'server', 'client',
            'frontend', 'backend', 'fullstack', 'rest', 'graphql', 'websocket',
            'security', 'ssl', 'tls', 'oauth', 'jwt', 'token', 'session',
            'performance', 'optimization', 'monitoring', 'logging', 'metrics'
        ]
        
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in technical_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        # Also extract capitalized words (likely to be important names/terms)
        capitalized_words = re.findall(r'\b[A-Z][a-zA-Z]+\b', content)
        found_keywords.extend(capitalized_words[:5])  # Limit to 5
        
        return list(set(found_keywords))[:10]  # Return unique keywords, max 10
    
    def generate_chunk_summary(self, content: str) -> str:
        """Generate a brief summary of the chunk content"""
        
        # Take first sentence or first 100 characters
        sentences = content.split('.')
        if sentences and len(sentences[0]) > 20:
            summary = sentences[0].strip() + '.'
        else:
            summary = content[:100].strip()
            if len(content) > 100:
                summary += '...'
        
        return summary

class VectorStore:
    """Handles storage and retrieval of document chunks in vector database"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create collections for different roles and content types
        self.collections = {
            'developer': self.client.get_or_create_collection(
                name="developer_docs",
                metadata={"description": "Documents relevant for developers"}
            ),
            'support': self.client.get_or_create_collection(
                name="support_docs", 
                metadata={"description": "Documents relevant for support engineers"}
            ),
            'manager': self.client.get_or_create_collection(
                name="manager_docs",
                metadata={"description": "Documents relevant for managers"}
            ),
            'general': self.client.get_or_create_collection(
                name="general_docs",
                metadata={"description": "General documentation"}
            )
        }
        
        logger.info(f"Vector store initialized with {len(self.collections)} collections")
    
    def _sanitize_metadata_for_chromadb(self, metadata: Dict) -> Dict:
        """Convert metadata to ChromaDB-compatible format (no lists, only primitives)"""
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, list):
                # Convert lists to comma-separated strings
                sanitized[key] = ', '.join(str(v) for v in value) if value else ''
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = ''
            else:
                # Convert other types to string
                sanitized[key] = str(value)
        return sanitized
    
    async def store_chunks(self, processed_chunks: List[ProcessedChunk]) -> None:
        """Store processed chunks in appropriate collections"""
        
        if not processed_chunks:
            return
        
        logger.info(f"Storing {len(processed_chunks)} chunks in vector database")
        
        for chunk in processed_chunks:
            # Determine which collections to store in based on role tags
            role_tags = chunk.metadata.get('role_tags', ['general'])
            target_collections = []
            
            for role in role_tags:
                if role in self.collections:
                    target_collections.append(role)
            
            # Fallback to general if no specific role matches
            if not target_collections:
                target_collections = ['general']
            
            # Sanitize metadata for ChromaDB (convert lists to strings)
            sanitized_metadata = self._sanitize_metadata_for_chromadb(chunk.metadata)
            
            # Store in each relevant collection
            for collection_name in target_collections:
                try:
                    self.collections[collection_name].add(
                        ids=[chunk.id],
                        embeddings=[chunk.embedding],
                        documents=[chunk.content],
                        metadatas=[sanitized_metadata]
                    )
                    
                    logger.debug(f"Stored chunk {chunk.id} in collection {collection_name}")
                    
                except Exception as e:
                    logger.error(f"Error storing chunk {chunk.id} in {collection_name}: {e}")
    
    async def search_similar(self, 
                           query: str, 
                           user_role: str = 'general',
                           n_results: int = 10,
                           filters: Optional[Dict] = None,
                           processor: Optional[DocumentProcessor] = None) -> List[Dict]:
        """Search for similar chunks based on query and user role"""
        
        # Determine which collections to search
        collections_to_search = ['general']
        if user_role in self.collections:
            collections_to_search.append(user_role)
        
        all_results = []
        
        for collection_name in collections_to_search:
            try:
                # Generate query embedding using provided processor or create new one
                if processor:
                    query_embedding = await processor.generate_embedding(query)
                else:
                    # Fallback to local embeddings
                    temp_processor = DocumentProcessor()
                    query_embedding = temp_processor.embedder.encode([query])[0].tolist()
                
                results = self.collections[collection_name].query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=['documents', 'metadatas', 'distances'],
                    where=filters
                )
                
                # Combine results with collection info
                for i in range(len(results['documents'][0])):
                    all_results.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'collection': collection_name
                    })
                    
            except Exception as e:
                logger.error(f"Error searching in collection {collection_name}: {e}")
        
        # Sort by distance (similarity) and return top results
        all_results.sort(key=lambda x: x['distance'])
        return all_results[:n_results]
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about stored documents"""
        stats = {}
        for name, collection in self.collections.items():
            stats[name] = collection.count()
        return stats

# Example pipeline orchestrator
class DocumentPipeline:
    """Orchestrates the entire document processing pipeline"""
    
    def __init__(self, 
                 vector_store: VectorStore,
                 processor: DocumentProcessor):
        self.vector_store = vector_store
        self.processor = processor
    
    async def process_and_store_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """Process and store a batch of documents"""
        
        logger.info(f"Starting pipeline for {len(documents)} documents")
        
        total_chunks = 0
        processed_documents = 0
        errors = 0
        
        for document in documents:
            try:
                # Process document into chunks
                chunks = await self.processor.process_document(document)
                
                if chunks:
                    # Store chunks in vector database
                    await self.vector_store.store_chunks(chunks)
                    print(f"✅ Generated {len(chunks)} chunks with embeddings and stored in vector DB")
                    total_chunks += len(chunks)
                    processed_documents += 1
                else:
                    logger.warning(f"No chunks generated for document from {document.source}")
                    
            except Exception as e:
                logger.error(f"Error in pipeline for document: {e}")
                errors += 1
        
        stats = {
            'processed_documents': processed_documents,
            'total_chunks': total_chunks,
            'errors': errors,
            'collection_stats': self.vector_store.get_collection_stats()
        }
        
        logger.info(f"Pipeline completed: {stats}")
        return stats

# Example usage
async def main():
    """Example of running the document processing pipeline"""
    
    # Initialize components
    processor = DocumentProcessor()
    vector_store = VectorStore()
    pipeline = DocumentPipeline(vector_store, processor)
    
    # Example document (you would get these from data_collectors.py)
    example_doc = Document(
        content="""# Authentication Service
        
        This service handles user authentication using OAuth 2.0.
        
        ## Setup
        
        1. Install dependencies: pip install -r requirements.txt
        2. Set environment variables: OAUTH_CLIENT_ID, OAUTH_SECRET
        3. Run the service: python app.py
        
        ## Troubleshooting
        
        Common issues:
        - Invalid client credentials: Check your OAUTH_CLIENT_ID
        - Token expired: Refresh tokens automatically handled
        """,
        source='github',
        doc_type='documentation', 
        role_tags=['developer', 'support'],
        metadata={
            'repository': 'auth-service',
            'file_path': 'README.md',
            'owner': 'myorg'
        }
    )
    
    # Process the document
    result = await pipeline.process_and_store_documents([example_doc])
    print(f"Processing result: {result}")
    
    # Test search
    search_results = await vector_store.search_similar(
        query="How to setup authentication?",
        user_role="developer",
        n_results=5
    )
    
    print(f"Found {len(search_results)} relevant chunks")
    for result in search_results:
        print(f"Distance: {result['distance']:.3f}")
        print(f"Content: {result['content'][:200]}...")
        print("---")

if __name__ == "__main__":
    asyncio.run(main())

