"""
AWS OpenSearch Serverless Vector Store Implementation
Replaces ChromaDB with AWS-managed vector database
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# AWS and OpenSearch imports
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from requests_aws4auth import AWS4Auth

from document_processor import ProcessedChunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenSearchVectorStore:
    """
    AWS OpenSearch Serverless vector store implementation
    Maintains compatibility with ChromaDB-based VectorStore interface
    """
    
    def __init__(self, 
                 endpoint: str,
                 region: str = "us-east-1",
                 index_prefix: str = "ai-org-assistant",
                 embedding_dimension: int = 1024):
        """
        Initialize OpenSearch Serverless client
        
        Args:
            endpoint: OpenSearch Serverless endpoint URL (e.g., https://xxxxx.us-east-1.aoss.amazonaws.com)
            region: AWS region
            index_prefix: Prefix for index names
            embedding_dimension: Vector dimension (1024 for BGE-Large, 1536 for Titan)
        """
        self.endpoint = endpoint.replace('https://', '')  # Remove https:// if present
        self.region = region
        self.index_prefix = index_prefix
        self.embedding_dimension = embedding_dimension
        
        # Get AWS credentials
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, 'aoss')
        
        # Initialize OpenSearch client
        self.client = OpenSearch(
            hosts=[{'host': self.endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
        
        # Define index names (matching ChromaDB collections)
        self.indexes = {
            'developer': f"{index_prefix}-developer",
            'support': f"{index_prefix}-support",
            'manager': f"{index_prefix}-manager",
            'general': f"{index_prefix}-general"
        }
        
        logger.info(f"OpenSearch Vector Store initialized")
        logger.info(f"Endpoint: {self.endpoint}")
        logger.info(f"Region: {region}")
        logger.info(f"Indexes: {list(self.indexes.values())}")
    
    async def create_indexes(self):
        """Create indexes with vector field mappings if they don't exist"""
        
        # Index mapping template
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512,
                    "number_of_shards": 2,
                    "number_of_replicas": 1
                }
            },
            "mappings": {
                "properties": {
                    "id": {
                        "type": "keyword"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": self.embedding_dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "source": {
                        "type": "keyword"
                    },
                    "doc_type": {
                        "type": "keyword"
                    },
                    "role_tags": {
                        "type": "keyword"
                    },
                    "source_document_id": {
                        "type": "keyword"
                    },
                    "chunk_index": {
                        "type": "integer"
                    },
                    "total_chunks": {
                        "type": "integer"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    }
                }
            }
        }
        
        # Create each index
        for collection_name, index_name in self.indexes.items():
            try:
                if not self.client.indices.exists(index=index_name):
                    self.client.indices.create(index=index_name, body=index_body)
                    logger.info(f"✅ Created index: {index_name}")
                else:
                    logger.info(f"ℹ️  Index already exists: {index_name}")
            except Exception as e:
                logger.error(f"❌ Error creating index {index_name}: {e}")
                raise
    
    def _prepare_document_for_indexing(self, chunk: ProcessedChunk) -> Dict[str, Any]:
        """Convert ProcessedChunk to OpenSearch document format"""
        
        # Flatten metadata for better searchability
        doc = {
            "id": chunk.id,
            "content": chunk.content,
            "embedding": chunk.embedding,
            "source_document_id": chunk.source_document_id,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            
            # Extract key fields from metadata for easier filtering
            "source": chunk.metadata.get('source', ''),
            "doc_type": chunk.metadata.get('doc_type', ''),
            "role_tags": chunk.metadata.get('role_tags', '').split(', ') if isinstance(chunk.metadata.get('role_tags'), str) else chunk.metadata.get('role_tags', []),
            
            # Dates
            "created_at": chunk.metadata.get('created_at'),
            "updated_at": chunk.metadata.get('updated_at'),
            
            # Store full metadata
            "metadata": chunk.metadata
        }
        
        return doc
    
    async def store_chunks(self, processed_chunks: List[ProcessedChunk]) -> None:
        """Store processed chunks in appropriate indexes"""
        
        if not processed_chunks:
            return
        
        logger.info(f"Storing {len(processed_chunks)} chunks in OpenSearch")
        
        # Ensure indexes exist
        await self.create_indexes()
        
        for chunk in processed_chunks:
            # Determine which indexes to store in based on role tags
            role_tags = chunk.metadata.get('role_tags', ['general'])
            
            # Convert comma-separated string to list if needed
            if isinstance(role_tags, str):
                role_tags = [tag.strip() for tag in role_tags.split(',')]
            
            target_indexes = []
            for role in role_tags:
                if role in self.indexes:
                    target_indexes.append(role)
            
            # Fallback to general if no specific role matches
            if not target_indexes:
                target_indexes = ['general']
            
            # Prepare document
            doc = self._prepare_document_for_indexing(chunk)
            
            # Store in each relevant index
            for collection_name in target_indexes:
                index_name = self.indexes[collection_name]
                
                try:
                    # OpenSearch Serverless requires using the direct HTTP API
                    # Use the low-level transport to make the request
                    # Format: POST /{index}/_doc with auto-generated ID or POST /{index}/_doc/{id}
                    response = await asyncio.to_thread(
                        self.client.transport.perform_request,
                        'POST',
                        f'/{index_name}/_doc',
                        body=doc
                    )
                    
                    # Get the generated ID from response
                    doc_id = response.get('_id', chunk.id)
                    logger.debug(f"Stored chunk as {doc_id} in index {index_name}")
                    
                except Exception as e:
                    logger.error(f"Error storing chunk {chunk.id} in {index_name}: {e}")
                    logger.debug(f"Error details: {type(e).__name__}: {str(e)}")
                    # Continue with other chunks even if one fails
    
    async def search_similar(self,
                           query: str,
                           user_role: str = 'general',
                           n_results: int = 10,
                           filters: Optional[Dict] = None,
                           processor = None) -> List[Dict]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query: Search query text
            user_role: User role for collection selection
            n_results: Number of results to return
            filters: Optional metadata filters
            processor: DocumentProcessor instance for generating query embedding
            
        Returns:
            List of result dictionaries with content, metadata, distance, collection
        """
        
        # Determine which indexes to search
        indexes_to_search = [self.indexes['general']]
        if user_role in self.indexes:
            indexes_to_search.append(self.indexes[user_role])
        
        # Generate query embedding
        if processor:
            query_embedding = await processor.generate_embedding(query)
        else:
            logger.warning("No processor provided, cannot generate query embedding")
            return []
        
        all_results = []
        
        for index_name in indexes_to_search:
            try:
                # Build OpenSearch KNN query
                knn_query = {
                    "size": n_results,
                    "query": {
                        "knn": {
                            "embedding": {
                                "vector": query_embedding,
                                "k": n_results
                            }
                        }
                    }
                }
                
                # Add filters if provided
                if filters:
                    bool_filter = self._build_filters(filters)
                    knn_query["query"] = {
                        "bool": {
                            "must": [knn_query["query"]],
                            "filter": bool_filter
                        }
                    }
                
                # Execute search
                response = await asyncio.to_thread(
                    self.client.search,
                    index=index_name,
                    body=knn_query
                )
                
                # Process results
                for hit in response['hits']['hits']:
                    # Calculate distance from score (OpenSearch returns similarity score)
                    # Convert similarity (0-1) to distance (higher = less similar)
                    distance = 1 - hit['_score'] if hit['_score'] <= 1 else 0
                    
                    result = {
                        'content': hit['_source']['content'],
                        'metadata': hit['_source'].get('metadata', {}),
                        'distance': distance,
                        'collection': index_name.replace(f"{self.index_prefix}-", "")
                    }
                    all_results.append(result)
                    
            except Exception as e:
                logger.error(f"Error searching in index {index_name}: {e}")
        
        # Sort by distance (lower is better) and return top results
        all_results.sort(key=lambda x: x['distance'])
        return all_results[:n_results]
    
    def _build_filters(self, filters: Dict) -> List[Dict]:
        """Convert filter dictionary to OpenSearch filter format"""
        
        filter_clauses = []
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Terms filter for lists
                filter_clauses.append({
                    "terms": {key: value}
                })
            else:
                # Term filter for single values
                filter_clauses.append({
                    "term": {key: value}
                })
        
        return filter_clauses
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about stored documents"""
        
        stats = {}
        
        for collection_name, index_name in self.indexes.items():
            try:
                # Check if index exists
                if self.client.indices.exists(index=index_name):
                    # Get document count
                    count_response = self.client.count(index=index_name)
                    stats[collection_name] = count_response['count']
                else:
                    stats[collection_name] = 0
            except Exception as e:
                logger.error(f"Error getting stats for {index_name}: {e}")
                stats[collection_name] = 0
        
        return stats
    
    async def delete_index(self, collection_name: str) -> bool:
        """Delete an entire index (use with caution)"""
        
        if collection_name not in self.indexes:
            logger.error(f"Invalid collection name: {collection_name}")
            return False
        
        index_name = self.indexes[collection_name]
        
        try:
            if self.client.indices.exists(index=index_name):
                await asyncio.to_thread(
                    self.client.indices.delete,
                    index=index_name
                )
                logger.info(f"Deleted index: {index_name}")
                return True
            else:
                logger.warning(f"Index does not exist: {index_name}")
                return False
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {e}")
            return False
    
    async def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents from a collection"""
        
        # Delete and recreate index
        await self.delete_index(collection_name)
        await self.create_indexes()
        return True
    
    def get_health(self) -> Dict[str, Any]:
        """Check OpenSearch cluster health"""
        
        try:
            health = self.client.cluster.health()
            return {
                "status": health['status'],
                "number_of_nodes": health['number_of_nodes'],
                "active_shards": health['active_shards'],
                "endpoint": self.endpoint
            }
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Backward compatibility: Alias for easy switching
VectorStore = OpenSearchVectorStore


# Example usage and testing
async def main():
    """Example usage of OpenSearch Vector Store"""
    
    import os
    from document_processor import DocumentProcessor
    from data_collectors import Document
    
    # Initialize
    endpoint = os.getenv("AWS_OPENSEARCH_ENDPOINT", "")
    if not endpoint:
        print("Set AWS_OPENSEARCH_ENDPOINT environment variable")
        return
    
    vector_store = OpenSearchVectorStore(
        endpoint=endpoint,
        region=os.getenv("AWS_OPENSEARCH_REGION", "us-east-1"),
        index_prefix="test-ai-org"
    )
    
    # Check health
    health = vector_store.get_health()
    print(f"Health: {health}")
    
    # Create indexes
    await vector_store.create_indexes()
    
    # Test with sample document
    processor = DocumentProcessor(use_aws_bedrock=True)
    
    test_doc = Document(
        content="""# Authentication Service
        
        This service handles user authentication using OAuth 2.0.
        
        ## Setup
        1. Install dependencies: pip install -r requirements.txt
        2. Set environment variables: OAUTH_CLIENT_ID, OAUTH_SECRET
        3. Run the service: python app.py
        """,
        source='github',
        doc_type='documentation',
        role_tags=['developer', 'support'],
        metadata={
            'repository': 'auth-service',
            'file_path': 'README.md'
        }
    )
    
    # Process and store
    chunks = await processor.process_document(test_doc)
    await vector_store.store_chunks(chunks)
    
    print(f"Stored {len(chunks)} chunks")
    
    # Search
    results = await vector_store.search_similar(
        query="How to setup authentication?",
        user_role="developer",
        n_results=5,
        processor=processor
    )
    
    print(f"\nSearch results: {len(results)}")
    for i, result in enumerate(results):
        print(f"{i+1}. Distance: {result['distance']:.3f}")
        print(f"   Content: {result['content'][:100]}...")
    
    # Get stats
    stats = vector_store.get_collection_stats()
    print(f"\nCollection stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())

