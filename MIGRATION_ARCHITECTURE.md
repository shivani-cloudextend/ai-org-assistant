# AWS Vector Database Migration - Architecture Diagrams

## Current Architecture (ChromaDB)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
├───────────────┬───────────────────┬─────────────────────────────────┤
│    GitHub     │    Confluence     │         Jira                    │
│  (via MCP)    │   (Atlassian)     │    (Atlassian)                 │
└───────┬───────┴─────────┬─────────┴─────────┬───────────────────────┘
        │                 │                   │
        └─────────────────┼───────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │      Data Collectors (data_collectors.py)   │
        │  - Fetch documents from all sources         │
        │  - Parse content and extract metadata       │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │   Document Processor (document_processor.py)│
        │  - Chunk documents (1000 chars, 200 overlap)│
        │  - Generate embeddings:                     │
        │    • Local: BAAI/bge-large-en-v1.5 (1024d) │
        │    • AWS: Titan Embed v1 (1536d)           │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │      ChromaDB (LOCAL FILE SYSTEM)           │
        │  Location: ./chroma_db/                     │
        │                                             │
        │  Collections:                               │
        │  ├─ developer_docs    (role: developer)    │
        │  ├─ support_docs      (role: support)      │
        │  ├─ manager_docs      (role: manager)      │
        │  └─ general_docs      (role: general)      │
        │                                             │
        │  Storage: Persistent local SQLite + vectors│
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │         AI Engine (ai_engine.py)            │
        │  - Semantic search via vector similarity    │
        │  - Role-based filtering                     │
        │  - Context retrieval (top-k results)        │
        │  - LLM: AWS Bedrock (Claude/Titan)          │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │         FastAPI REST API (main.py)          │
        │  Endpoints:                                 │
        │  - POST /query        (ask questions)       │
        │  - POST /sync         (refresh data)        │
        │  - GET  /health       (check status)        │
        │  - GET  /collections/stats                  │
        └─────────────────────────────────────────────┘
```

### Current Limitations
- ❌ Single server (no high availability)
- ❌ Limited scalability (file-based storage)
- ❌ Manual backups required
- ❌ No built-in monitoring
- ❌ No multi-region support

---

## New Architecture (AWS OpenSearch Serverless)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
├───────────────┬───────────────────┬─────────────────────────────────┤
│    GitHub     │    Confluence     │         Jira                    │
│  (via MCP)    │   (Atlassian)     │    (Atlassian)                 │
└───────┬───────┴─────────┬─────────┴─────────┬───────────────────────┘
        │                 │                   │
        └─────────────────┼───────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │      Data Collectors (data_collectors.py)   │
        │  - Fetch documents from all sources         │
        │  - Parse content and extract metadata       │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │   Document Processor (document_processor.py)│
        │  - Chunk documents (1000 chars, 200 overlap)│
        │  - Generate embeddings:                     │
        │    • Local: BAAI/bge-large-en-v1.5 (1024d) │
        │    • AWS: Titan Embed v1 (1536d)           │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ╔═════════════════════════════════════════════╗
        ║  AWS OpenSearch Serverless (NEW!)           ║
        ║  Region: us-east-1                          ║
        ║  Collection: ai-org-assistant-vectors       ║
        ║                                             ║
        ║  Indexes (with vector fields):              ║
        ║  ├─ ai-org-assistant-developer              ║
        ║  │  └─ Vector field: embedding (1024/1536d) ║
        ║  │     Algorithm: HNSW (cosine similarity)  ║
        ║  ├─ ai-org-assistant-support                ║
        ║  ├─ ai-org-assistant-manager                ║
        ║  └─ ai-org-assistant-general                ║
        ║                                             ║
        ║  Features:                                  ║
        ║  ✓ Auto-scaling (OCU-based)                ║
        ║  ✓ High availability (multi-AZ)            ║
        ║  ✓ Automatic backups                        ║
        ║  ✓ CloudWatch monitoring                    ║
        ║  ✓ IAM access control                       ║
        ╚═════════════════╦═══════════════════════════╝
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │    OpenSearch Vector Store                  │
        │    (aws_vector_store.py - NEW!)             │
        │                                             │
        │  - Drop-in replacement for ChromaDB         │
        │  - Async operations                         │
        │  - HNSW vector search                       │
        │  - Role-based index routing                 │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │         AI Engine (ai_engine.py)            │
        │  - Semantic search via vector similarity    │
        │  - Role-based filtering                     │
        │  - Context retrieval (top-k results)        │
        │  - LLM: AWS Bedrock (Claude/Titan)          │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │         FastAPI REST API (main.py)          │
        │  Endpoints:                                 │
        │  - POST /query        (ask questions)       │
        │  - POST /sync         (refresh data)        │
        │  - GET  /health       (check status)        │
        │  - GET  /collections/stats                  │
        └──────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │         AWS Services Integration            │
        │  - CloudWatch: Logs & Metrics               │
        │  - IAM: Access control                      │
        │  - Bedrock: LLM & Embeddings                │
        │  - CloudTrail: Audit logs                   │
        └─────────────────────────────────────────────┘
```

### New Capabilities
- ✅ High availability across multiple AZs
- ✅ Auto-scaling based on workload
- ✅ Automatic backups and recovery
- ✅ Built-in monitoring (CloudWatch)
- ✅ Enterprise-grade security (IAM, VPC)
- ✅ Scales to millions of documents

---

## Migration Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MIGRATION PROCESS                                │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Prerequisites
├─ AWS Account Setup
├─ IAM Permissions
└─ AWS CLI Configuration

Step 2: Infrastructure Setup
├─ Run: python setup_aws_opensearch.py
│   ├─ Create OpenSearch Serverless collection
│   ├─ Configure security policies
│   ├─ Create vector indexes
│   └─ Update .env configuration
└─ Wait: 5-10 minutes (collection activation)

Step 3: Testing
├─ Run: python test_opensearch_integration.py
│   ├─ Test connection
│   ├─ Test index creation
│   ├─ Test document storage
│   ├─ Test search functionality
│   ├─ Test role-based filtering
│   └─ Test performance
└─ Verify: All tests pass

Step 4: Application Update
├─ Update .env: VECTOR_DB_TYPE=opensearch
├─ Start: python main.py
└─ Verify: Application starts successfully

Step 5: Data Migration
├─ Trigger: POST /sync API
│   ├─ Fetch from GitHub
│   ├─ Fetch from Confluence
│   ├─ Fetch from Jira
│   ├─ Generate embeddings
│   └─ Store in OpenSearch
└─ Monitor: Check /collections/stats

Step 6: Validation
├─ Compare search results (ChromaDB vs OpenSearch)
├─ Validate query performance
├─ Check role-based filtering
└─ Verify data completeness

Step 7: Production Deployment
├─ Update production environment
├─ Deploy application
├─ Monitor CloudWatch metrics
└─ Decommission ChromaDB

Step 8: Optimization
├─ Review performance metrics
├─ Optimize index settings if needed
├─ Configure cost alerts
└─ Set up monitoring dashboards
```

---

## Component Interaction - Query Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER QUERY PROCESSING                            │
└─────────────────────────────────────────────────────────────────────┘

1. User Request
   ↓
   POST /query
   {
     "question": "How to deploy auth service?",
     "user_role": "developer"
   }

2. FastAPI Endpoint (main.py)
   ↓
   ├─ Validate user role
   ├─ Create QueryContext
   └─ Call ai_engine.process_query()

3. AI Engine (ai_engine.py)
   ↓
   ├─ Generate query embedding
   │  ├─ Local: SentenceTransformer
   │  └─ AWS: Bedrock Titan
   │
   ├─ Retrieve relevant docs
   │  ↓
   │  ┌────────────────────────────────────────┐
   │  │   OpenSearch Vector Search             │
   │  │                                        │
   │  │   Query:                               │
   │  │   - KNN search with embedding vector   │
   │  │   - Index: developer + general         │
   │  │   - Algorithm: HNSW cosine similarity  │
   │  │   - Results: Top 15 documents          │
   │  │                                        │
   │  │   Response:                            │
   │  │   - Documents with similarity scores   │
   │  │   - Metadata (source, type, etc.)      │
   │  │   - Distance metrics                   │
   │  └────────────────────────────────────────┘
   │
   ├─ Filter by role relevance
   ├─ Rerank results (top 8)
   │
   └─ Build role-specific prompt
      ↓
      ┌────────────────────────────────────────┐
      │   AWS Bedrock (Claude/Titan)           │
      │                                        │
      │   Prompt:                              │
      │   - System prompt (role-specific)      │
      │   - Context (retrieved documents)      │
      │   - User question                      │
      │                                        │
      │   Response:                            │
      │   - Comprehensive answer               │
      │   - Citations to sources               │
      │   - Suggested actions                  │
      └────────────────────────────────────────┘
      ↓

4. Response Formation
   ↓
   {
     "answer": "To deploy auth service...",
     "confidence_score": 0.85,
     "sources": [...],
     "role_specific_notes": [...],
     "suggested_actions": [...]
   }
```

---

## Data Flow - Document Indexing

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT INDEXING FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

1. Trigger Sync
   POST /sync {"sources": ["github", "confluence"]}

2. Data Collection (data_collectors.py)
   ↓
   ├─ GitHub
   │  ├─ Discover repositories
   │  ├─ Fetch README, docs, code
   │  ├─ Extract issues, PRs
   │  └─ Classify by role (developer/support)
   │
   ├─ Confluence
   │  ├─ Fetch pages from spaces
   │  ├─ Parse HTML content
   │  ├─ Extract metadata, labels
   │  └─ Classify by role
   │
   └─ Create Document objects

3. Document Processing (document_processor.py)
   ↓
   ├─ Clean content
   ├─ Choose text splitter (markdown/python/generic)
   ├─ Chunk document
   │  ├─ Size: 1000 characters
   │  ├─ Overlap: 200 characters
   │  └─ Context-aware splitting
   │
   ├─ Generate embeddings (batch)
   │  ├─ Local: BAAI/bge-large-en-v1.5 → 1024d vectors
   │  └─ AWS: Titan Embed v1 → 1536d vectors
   │
   ├─ Enrich metadata
   │  ├─ Keywords extraction
   │  ├─ Complexity scoring
   │  ├─ Content classification
   │  └─ Token counting
   │
   └─ Create ProcessedChunk objects

4. Storage (aws_vector_store.py)
   ↓
   ├─ Determine target indexes (based on role_tags)
   │  ├─ developer → ai-org-assistant-developer
   │  ├─ support   → ai-org-assistant-support
   │  ├─ manager   → ai-org-assistant-manager
   │  └─ general   → ai-org-assistant-general
   │
   └─ Index in OpenSearch
      ├─ Document fields:
      │  ├─ id (unique)
      │  ├─ content (text)
      │  ├─ embedding (vector)
      │  ├─ metadata (object)
      │  └─ timestamps
      │
      ├─ Vector search configuration:
      │  ├─ Method: HNSW
      │  ├─ Space: Cosine similarity
      │  ├─ Parameters: ef_construction=512, m=16
      │  └─ Dimension: 1024 or 1536
      │
      └─ Store with refresh=True (immediate availability)

5. Verification
   ↓
   ├─ Check collection stats
   ├─ Verify document count
   └─ Test search functionality
```

---

## Cost Comparison

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COST ANALYSIS                                    │
└─────────────────────────────────────────────────────────────────────┘

CHROMADB (Self-Hosted)
├─ EC2 Instance (t3.medium, 24/7)
│  └─ Cost: ~$30-50/month
├─ EBS Storage (100 GB)
│  └─ Cost: ~$10/month
├─ Backups (S3)
│  └─ Cost: ~$2-5/month
├─ Data Transfer
│  └─ Cost: ~$5-10/month
└─ TOTAL: ~$50-75/month
   + Maintenance time: ~5 hours/month
   + Single point of failure risk

AWS OPENSEARCH SERVERLESS
├─ Indexing OCU (1-2 units, 24/7)
│  └─ Cost: $0.24/hour × 1 OCU × 730 hours = ~$175/month
├─ Search OCU (1-2 units, 24/7)
│  └─ Cost: $0.24/hour × 1 OCU × 730 hours = ~$175/month
├─ Storage (10-50 GB)
│  └─ Cost: $0.024/GB × 50 GB = ~$1.20/month
├─ Data Transfer (minimal)
│  └─ Cost: ~$1-2/month
└─ TOTAL: ~$350-400/month
   + Zero maintenance
   + High availability
   + Auto-scaling
   + Built-in monitoring

EMBEDDINGS COST (Optional)
├─ Local (BGE-Large)
│  └─ Cost: $0 (uses CPU/GPU)
└─ AWS Bedrock Titan
   └─ Cost: $0.0001/1K tokens
   └─ ~$0.10 per 1000 documents
   └─ Initial indexing: $10-50 one-time
   └─ Ongoing queries: $5-20/month

TOTAL COST COMPARISON (Monthly)
├─ ChromaDB:  $50-75  + 5 hours maintenance
└─ OpenSearch: $350-400 + 0 hours maintenance

ROI BREAK-EVEN
├─ Additional cost: ~$300/month
├─ Time saved: ~5 hours/month
└─ If your time is worth > $60/hour → OpenSearch is cheaper
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                                  │
└─────────────────────────────────────────────────────────────────────┘

1. Network Security
   ├─ Public Access (development)
   │  └─ HTTPS only (TLS 1.2+)
   │
   └─ VPC Access (production recommended)
      ├─ Private subnet
      ├─ Security groups
      └─ Network ACLs

2. Authentication & Authorization
   ├─ AWS IAM
   │  ├─ User/Role-based access
   │  ├─ Least privilege principle
   │  └─ MFA enabled
   │
   ├─ Data Access Policies
   │  ├─ Collection-level permissions
   │  ├─ Index-level permissions
   │  └─ Document-level filtering
   │
   └─ Service-to-service
      └─ AWSV4SignerAuth (SigV4)

3. Data Protection
   ├─ Encryption at rest
   │  ├─ AWS-managed key (default)
   │  └─ Customer-managed key (KMS option)
   │
   ├─ Encryption in transit
   │  └─ TLS 1.2+ (HTTPS)
   │
   └─ Data isolation
      └─ Multi-tenant with logical separation

4. Audit & Compliance
   ├─ CloudTrail
   │  └─ All API calls logged
   │
   ├─ CloudWatch Logs
   │  └─ Application and access logs
   │
   └─ Compliance
      ├─ SOC 2 Type II
      ├─ HIPAA eligible
      └─ GDPR compliant
```

---

## Monitoring & Alerting

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MONITORING SETUP                                 │
└─────────────────────────────────────────────────────────────────────┘

CloudWatch Metrics (Automatic)
├─ SearchRate (requests/second)
├─ IndexingRate (documents/second)
├─ SearchLatency (milliseconds)
│  └─ Alarm: > 500ms
├─ IndexingLatency (milliseconds)
├─ SearchableDocuments (count)
├─ DeletedDocuments (count)
├─ SearchOCU (OpenSearch Compute Units)
│  └─ Alarm: High utilization
├─ IndexingOCU (OpenSearch Compute Units)
│  └─ Alarm: High utilization
└─ 4xx/5xx Errors (count)
   └─ Alarm: > 1% error rate

CloudWatch Dashboards
├─ Real-time metrics
├─ Historical trends
├─ Cost analysis
└─ Performance overview

Application Logging
├─ Request/response logging
├─ Error tracking
├─ Performance profiling
└─ User query analytics

Recommended Alarms
├─ High latency (> 500ms)
├─ High error rate (> 1%)
├─ High cost (> budget)
├─ Low success rate (< 95%)
└─ OCU saturation (> 80%)
```

This completes the comprehensive AWS Vector Database migration architecture!




