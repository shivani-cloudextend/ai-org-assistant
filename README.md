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
- **Vector Database**: ChromaDB
- **Embeddings**: AWS Bedrock (Titan), OpenAI, or Sentence-Transformers
- **LLM**: OpenAI GPT-4 or local models
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
