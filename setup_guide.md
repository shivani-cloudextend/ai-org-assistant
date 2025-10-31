# AI Organization Assistant - Setup Guide

## Quick Start

### 1. Environment Setup

Create a `.env` file with your configuration:

```bash
# Copy the example and edit
cp .env.example .env
```

Required environment variables:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# GitHub Configuration (Required)
GITHUB_ORG=your-github-organization
GITHUB_TOKEN=ghp_your-github-token

# Confluence Configuration (Optional)
CONFLUENCE_URL=https://yourorg.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
CONFLUENCE_SPACE_KEYS=DEV,SUPPORT,DOCS

# Jira Configuration (Optional)  
JIRA_URL=https://yourorg.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECTS=PROJ1,PROJ2
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Application

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## Detailed Configuration

### GitHub Setup

1. Create a GitHub Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token with `repo` scope
   - Set as `GITHUB_TOKEN` in `.env`

2. Configure your organization:
   - Set `GITHUB_ORG` to your GitHub organization name
   - Optionally specify repositories in `GITHUB_REPOS` (comma-separated)

### Confluence Setup (Optional)

1. Get API Token:
   - Go to Atlassian Account Settings → Security → API tokens
   - Create new token
   - Set as `CONFLUENCE_API_TOKEN` in `.env`

2. Configure spaces:
   - Set `CONFLUENCE_SPACE_KEYS` to comma-separated space keys you want to index

### OpenAI Setup

1. Get API Key:
   - Go to OpenAI API dashboard
   - Create new API key
   - Set as `OPENAI_API_KEY` in `.env`

## Usage Examples

### 1. Initial Data Sync

After starting the application, sync your data sources:

#### **Basic Sync (All Sources)**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github", "confluence"]
  }'
```

#### **GitHub Only - Specific Repositories**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["suiteapps", "backend_services"]
  }'
```

#### **Confluence Only - Specific Spaces**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["confluence"],
    "spaces": ["CEOL", "TECH", "SUPPORT"]
  }'
```

#### **GitHub with Folder Filtering (Global)**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["main-app"],
    "include_paths": ["src/", "lib/"],
    "exclude_paths": ["tests/", "docs/"]
  }'
```

#### **GitHub with Per-Repository Filtering**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["main-app", "auth-service"],
    "repo_configs": {
      "main-app": {
        "include_paths": ["src/", "config/"],
        "exclude_paths": ["tests/"]
      },
      "auth-service": {
        "include_paths": ["core/", "api/"]
      }
    }
  }'
```

#### **Combined GitHub + Confluence Sync**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github", "confluence"],
    "repositories": ["main-app", "auth-service"],
    "spaces": ["DEV", "SUPPORT"]
  }'
```

### 2. Query as Developer

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I deploy the authentication service?",
    "user_role": "developer",
    "additional_context": "production environment"
  }'
```

### 3. Query as Support Engineer

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "User getting authentication errors, how to troubleshoot?",
    "user_role": "support",
    "additional_context": "customer reported issue"
  }'
```

### 4. Query with Source Filtering

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How are files uploaded to OneDrive and why might it fail?",
    "user_role": "developer",
    "filters": {
      "source": "github",
      "repository": "backend_services"
    }
  }'
```

### 5. Check System Status

```bash
curl http://localhost:8000/health
```

### 6. View Collection Statistics

```bash
curl http://localhost:8000/collections/stats
```

### 7. Check Sync Status

```bash
curl http://localhost:8000/sync/status
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Architecture Overview

```
User Query → FastAPI → AI Engine → Vector Search → LLM → Role-Based Response
                ↓
          Background Sync ← Data Collectors ← GitHub/Confluence/Jira APIs
                ↓
          Document Processing → Chunking → Embedding → Vector Storage
```

## Customization

### Adding New Data Sources

1. Create a new connector in `data_collectors.py`
2. Implement the `collect_all_data()` async generator
3. Add sync logic in `main.py`

### Modifying Role Behaviors

Edit the role prompts in `ai_engine.py`:

```python
self.role_prompts = {
    UserRole.DEVELOPER: {
        "system_prompt": "Your custom developer prompt...",
        # ... rest of configuration
    }
}
```

### Custom Embedding Models

Change the embedding model in `document_processor.py`:

```python
self.embedder = SentenceTransformer('your-preferred-model')
```

## Troubleshooting

### Common Issues

1. **"AI engine not initialized"**
   - Check that `OPENAI_API_KEY` is set correctly
   - Verify API key has sufficient credits

2. **"No relevant documents found"** 
   - Run data sync first: `POST /sync`
   - Check that sources are configured correctly
   - Verify sync completed successfully: `GET /sync/status`

3. **GitHub sync fails**
   - Check `GITHUB_TOKEN` permissions
   - Verify organization name is correct
   - Check rate limits

4. **Confluence sync fails**
   - Verify API token and credentials
   - Check space keys exist and are accessible
   - Ensure user has read permissions

### Logs

Check application logs for detailed error information:
```bash
tail -f logs/app.log  # If configured with file logging
```

### Performance Tuning

For large organizations:

1. **Batch Processing**: Modify sync to process in smaller batches
2. **Selective Sync**: Specify only important repositories/spaces  
3. **Embedding Model**: Use smaller model for faster processing
4. **Vector Store**: Consider Pinecone or Weaviate for better performance

## Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Environment Variables for Production

```bash
ENVIRONMENT=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info

# Use stronger embedding model
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# Production vector store
CHROMA_PERSIST_DIRECTORY=/data/chroma_db

# Sync settings
SYNC_INTERVAL_HOURS=12
```

### Security Considerations

1. **API Keys**: Use secure secret management
2. **CORS**: Configure allowed origins properly
3. **Authentication**: Add API authentication if needed
4. **Rate Limiting**: Implement request rate limiting
5. **HTTPS**: Use HTTPS in production

## Monitoring

### Health Checks
- `GET /health` - System health
- `GET /collections/stats` - Data statistics  
- `GET /sync/status` - Sync status

### Metrics to Monitor
- Query response times
- Embedding generation time
- Sync success rates
- Vector store size
- API error rates

## Support

For issues or questions:
1. Check the logs for error details
2. Verify configuration settings
3. Test with example queries
4. Review API documentation at `/docs`

