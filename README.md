# AI Organization Assistant

An intelligent assistant that reads and processes your organization's GitHub repositories, Confluence, and Jira documents to provide role-based responses to user queries.

## Features

- **Multi-source Data Ingestion**: GitHub repos, Confluence pages, Jira tickets
- **Role-based Responses**: Different answers for developers vs support engineers
- **Semantic Search**: Vector-based similarity search for relevant documents
- **Real-time Updates**: Periodic sync with data sources
- **RESTful API**: Easy integration with existing tools

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub API    │    │ Confluence API  │    │    Jira API     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │    Data Ingestion Layer     │
                    └─────────────┬───────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │   Document Processing       │
                    │   (Parse, Chunk, Embed)     │
                    └─────────────┬───────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │     Vector Database         │
                    │      (ChromaDB)             │
                    └─────────────┬───────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │      AI Engine              │
                    │   (Role-based Responses)    │
                    └─────────────┬───────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │       REST API              │
                    │    (Query Interface)        │
                    └─────────────────────────────┘
```

## Tech Stack

- **Backend**: Python/FastAPI
- **Vector Database**: 
  - **Production**: AWS OpenSearch Serverless (recommended)
  - **Development**: ChromaDB (local)
- **Embeddings**: 
  - AWS Bedrock Titan (1536d)
  - Sentence-Transformers BAAI/bge-large-en-v1.5 (1024d)
- **LLM**: AWS Bedrock (Claude 3 Haiku/Sonnet, Titan)
- **Data Processing**: Langchain
- **Frontend**: React (optional)

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

   Required environment variables:

   - `GITHUB_TOKEN`: GitHub personal access token
   - `GITHUB_ORG`: Your GitHub organization name
   - `OPENAI_API_KEY`: OpenAI API key (optional, for query responses)

   **AWS Bedrock Configuration** (optional, for embeddings):

   - `USE_AWS_BEDROCK=true`: Enable AWS Bedrock for embeddings
   - `AWS_REGION`: AWS region (default: us-east-1)

   **Confluence Configuration** (optional):

   - `CONFLUENCE_URL`: Your Confluence instance URL
   - `CONFLUENCE_USERNAME`: Confluence username/email
   - `CONFLUENCE_API_TOKEN`: Confluence API token
   - `CONFLUENCE_SPACE_KEYS`: Comma-separated space keys

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

### Query API

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How to deploy the authentication service?",
    "user_role": "developer",
    "context": "production deployment"
  }'
```

### Role-based Responses

**Developer Query**: "Authentication service deployment"

- Returns: Technical documentation, deployment scripts, configuration details

**Support Engineer Query**: "Authentication service deployment"

- Returns: Troubleshooting steps, common issues, monitoring guides

Command for killing the server process -> lsof -ti:8000 | xargs kill -9

## 🚀 AWS Vector Database Migration

This project supports both local ChromaDB and AWS OpenSearch Serverless for vector storage.

### Quick Migration to AWS OpenSearch

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure AWS credentials
aws configure

# 3. Run automated setup
python setup_aws_opensearch.py

# 4. Update .env
VECTOR_DB_TYPE=opensearch

# 5. Test connection
python test_opensearch_integration.py

# 6. Start application
python main.py

# 7. Sync your data
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{"sources": ["github", "confluence"]}'
```

### Documentation

- **📖 Quick Start**: [AWS_QUICK_START.md](./AWS_QUICK_START.md) - 10-minute setup guide
- **📚 Complete Guide**: [AWS_VECTOR_DB_MIGRATION_GUIDE.md](./AWS_VECTOR_DB_MIGRATION_GUIDE.md) - Comprehensive migration documentation
- **🎯 Summary**: [MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md) - Executive overview
- **🏗️ Architecture**: [MIGRATION_ARCHITECTURE.md](./MIGRATION_ARCHITECTURE.md) - Visual diagrams and flows

### Key Benefits

- ✅ **Scalable**: Handle millions of documents
- ✅ **High Availability**: Multi-AZ deployment
- ✅ **Managed**: Zero infrastructure maintenance
- ✅ **Monitored**: CloudWatch integration
- ✅ **Secure**: IAM, encryption, audit logs

### Cost Estimate

- **Small deployment** (~10K docs): ~$350/month
- **Medium deployment** (~100K docs): ~$700/month
- Includes auto-scaling, backups, monitoring

See [AWS_VECTOR_DB_MIGRATION_GUIDE.md](./AWS_VECTOR_DB_MIGRATION_GUIDE.md) for detailed cost analysis.
